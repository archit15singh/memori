# Factual freshness and access

Memori records factual age separately from usage:

| Clock | Advances when |
| --- | --- |
| `created_at` | The record is first inserted |
| `updated_at` | Content, vector, metadata or explicit validation changes |
| `content_updated_at` | Content bytes change |
| `validated_at` | A caller explicitly revalidates the current content |
| `last_accessed` / `access_count` | `get` reads a record |

Identical-content updates, metadata/tag edits, embedding backfills, searches,
related queries and reads leave factual freshness unchanged. A content edit
clears the previous validation because it referred to the previous content.
`get_readonly` and dashboard browsing leave access counters unchanged too.

```bash
# Verify the fact against its source first, then record that validation.
memori revalidate <id-or-prefix> --json
```

```python
db.revalidate(memory_id)
review = db.stale(before=cutoff_epoch_seconds, limit=5)
```

Revalidation records the caller's assertion. Memori does not check factual truth,
consult an LLM, or infer that a popular memory is correct. Use explicit lifecycle
operations for invalid facts once that feature is available; age ranking itself
does not expire or remove any memory.

## Ranking

```text
freshness_at = max(content_updated_at, validated_at if present)
popularity = 1 + min(0.5, 0.1 * ln(1 + max(access_count, 0)))
age_days = max(0, (now - freshness_at) / 86400)
adjustment = popularity * exp(-0.01 * age_days)
score = base_score * adjustment                 # nonnegative base
score = base_score / max(adjustment, MIN_POSITIVE) # negative cosine
```

The previous approximately 69-day half-life remains, now anchored to content or
explicit validation rather than reads. Never-accessed old records decay too.
Popularity is capped at 1.5x and cannot grow without bound. Future clocks do not
give extra freshness boost; they have zero age until wall time catches up.
Negative cosine scores use the inverse adjustment so decay cannot improve an
old negative match. The denominator is bounded to keep valid cosine scores finite.

Vector and FTS candidate scoring applies this policy before truncation. Hybrid
search then fuses the candidate ranks with RRF, so its final score is still not
cosine, confidence or factual validity. An optional semantic floor still acts
before popularity/age scoring. FTS now examines all matching candidates before
choosing the highest adjusted scores; broad keyword queries can cost more than
the old BM25-first SQL limit. No new performance benchmark is claimed.

`context` stale review now selects records whose factual clock is older than 30
days, including frequently read or recently tagged records. It queries the full
eligible set before limiting, instead of inspecting 20 creation-ordered records.
Explicitly revalidated or content-corrected records leave stale review. Recent
and frequent sections remain browsing aids, not claims that records are valid.

The dashboard detail panel shows **Content Changed** and **Explicitly Validated**
alongside modification/access dates. It remains read-only; use the explicit CLI
or Python operation after checking the fact.

## Migration and backups

Schema version 4 adds `content_updated_at` and nullable `validated_at`. The upgrade
uses one immediate transaction, including older migrations. A failed upgrade
rolls back its columns and version; a database from a newer schema is rejected.

For existing v3 records, `content_updated_at` starts at the existing `updated_at`
and `validated_at` starts null. Legacy databases did not distinguish tag edits
from content edits, so this initial clock is an approximation of the last known
write, not recovered content history or proof of validation. New tag edits do
not advance it. Revalidate or correct legacy facts after checking their sources.

Back up the database before upgrading. Older binaries do not understand the new
clocks and may write defaults rather than maintaining them; use the upgraded
binary for every writer. Rolling back requires restoring the pre-upgrade backup.

CLI JSONL export/import preserves both clocks, including `--new-ids`: changing an
ID is not revalidation. Older backups without clocks use their `updated_at` as
the initial approximation. Restored timestamps must be finite; invalid clocks
are rejected before inserting the record. Rust callers can use
`insert_with_id_and_freshness(..., Freshness { ... })`; the existing
`insert_with_id` method remains available with legacy-clock initialization.

Memory responses now include the two new fields. Rust consumers constructing
`Memory` literals must supply them; exhaustive error matches must handle
`InvalidTimestamp` and `UnsupportedSchema`. `schema::init_db` now returns the
crate's `Result` so callers can distinguish an unsupported schema.

## Verification

`freshness_test.rs` covers a real v3 database upgrade, repeated open, preserved
FTS/access state, failed migration rollback, future-version rejection, atomic
content/metadata update rollback, stale selection and invalid restore clocks.
The same tests run without embeddings.

A live database created by the preceding source build at schema v3 was upgraded
to v4. After three reads and a metadata edit, a 200-day-old fact retained its old
content clock and remained in stale review (score 0.1541 versus 0.9900 for a
one-day-old fact with the same vector). Explicit CLI revalidation advanced only
the validation/modification clocks, preserved the access count at three, and
removed the fact from stale review. The dashboard showed the old content date
separately from the new validation date.

`test_freshness.py` exercises aging without access, unchanged clocks after reads
and tags, explicit revalidation, bounded popularity, FTS ranking before top-k,
CLI stale review and backup/import with both original and new IDs. These use the
source-built native extension, real SQLite and CLI subprocesses.
