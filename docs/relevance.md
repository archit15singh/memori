# Relevance filtering

`min_similarity` is an optional, inclusive cosine floor in `[-1, 1]`. It rejects
weak semantic candidates before access scoring, candidate truncation and RRF.
The default is `None`: existing callers retain their retrieval behavior.

```python
hits = db.search(text="database architecture", min_similarity=0.4)
neighbors = db.related(memory_id, min_similarity=0.4)
```

```bash
memori search --text "database architecture" --min-similarity 0.4
memori context "database architecture" --min-similarity 0.4 --json
memori related <id> --min-similarity 0.4 --json
```

These values illustrate syntax, not a recommended universal cutoff.

## What the floor means

- Vector-only search requires raw cosine at least the floor. Popularity cannot
  rescue a candidate below it. Returned `score` remains the access-adjusted score.
- Hybrid search gates the vector leg. Literal FTS matches, including matches in
  metadata, remain eligible even below the cosine floor or without embeddings.
  Returned `score` remains RRF, not cosine or a probability of relevance.
- `context` applies the floor to `matches`. Its `recent`, `frequent`, and `stale`
  sections are browsing aids and can still contain unrelated records.
- Related-memory search uses the source vector, excludes the source itself, and
  applies the same cosine floor. Existing Rust `related(id, limit)` is unchanged;
  use `related_with_min_similarity(id, limit, Some(floor))` to opt in.
- Recent browsing and `text_only=True` reject a supplied floor. Text queries
  require the embeddings feature; builds without it must supply a vector.
- NaN, infinity and out-of-range floors are errors. A thresholded vector query
  must be finite, nonempty and nonzero. Stored vectors that are invalid or have
  different dimensions are skipped in the vector leg. Literal matches can still
  include those records. Cosine is calculated with f64 accumulation for this gate.

The dashboard's **Search cosine** field controls text search only. Leave it blank
to disable the floor. It does not change graph edges or detail-panel neighbors.
The HTTP search and related endpoints accept `min_similarity`; invalid values
return HTTP 400. CLI input errors return exit code 2 and structured stderr with
`--json`. The Python binding raises `RuntimeError` for core validation errors.

The Rust `SearchQuery` has a new field and `MemoriError` a new variant. Consumers
using exhaustive struct literals must add `min_similarity: None` (or use
`..Default::default()`); exhaustive error matches must handle `InvalidSimilarity`.
No database migration is needed.

## Calibration fixture

Run against a source-built extension:

```bash
.venv/bin/python scripts/eval-relevance.py
.venv/bin/python scripts/eval-relevance.py --dataset your-labels.json --limit 5 --thresholds none 0.2 0.3 0.4
```

The JSON output includes retrieved document IDs per query and micro-averaged
precision/recall, false positives, false negatives and correct abstentions. Labels
use the format in [the fixture](evals/relevance.json): stable memory IDs plus
queries with explicit relevant-ID lists, including queries with no relevant IDs.

Observed on 12 November 2026 with AllMiniLM-L6-V2, vector-only retrieval, top 3,
six synthetic memories and nine hand-labeled queries (three unanswerable):

| Floor | True positives | False positives | False negatives | Precision | Recall | Correct abstentions |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| None | 6 | 21 | 0 | 22.2% | 100% | 0/3 |
| 0.25 | 6 | 2 | 0 | 75% | 100% | 3/3 |
| 0.40 | 5 | 0 | 1 | 100% | 83.3% | 3/3 |
| 0.55 | 3 | 0 | 3 | 100% | 50% | 3/3 |
| 0.70 | 1 | 0 | 5 | 100% | 16.7% | 3/3 |

This is a calibration example, not a production benchmark or held-out evaluation.
Increasing the floor loses useful paraphrases. No default is selected from this
tiny fixture. Use representative project queries, label hard negatives, tune on
one set and validate on separate held-out queries before choosing a caller's
cutoff. Repeat when the model, corpus or retrieval mode changes. This script
isolates semantic filtering; it does not measure hybrid FTS behavior, lifecycle
validity, contradiction resolution or factual truth.

## Verification

Rust regression tests cover pre-boost filtering, hybrid literal preservation,
inclusive boundaries, related-prefix lookup, invalid vectors, invalid floors,
and builds without embeddings. Python tests exercise the native extension, CLI
search/context/related, and a real local HTTP server. The dashboard flow is also
checked interactively: unrelated banana-bread results disappear at `0.4`, a
PostgreSQL literal match remains, and `1.1` shows a validation message.
