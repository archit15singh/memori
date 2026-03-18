# Memori

**Persistent memory for AI coding agents. Rust + SQLite + FTS5 + vector search in a single file.**

AI coding agents forget everything between sessions. Memori gives them a persistent memory layer that accumulates knowledge over time — so every session starts with the context it needs, not from zero.

After `memori setup`, Claude Code automatically recalls debugging lessons before investigating bugs, stores architecture decisions with rationale, remembers your tool preferences, and self-maintains its own memory. No human intervention needed.

---

## What developers get

- **Session continuity** — Your agent remembers the bug you debugged yesterday, the architecture decision from last week, and that you prefer Tailwind over Bootstrap.
- **Zero config** — One SQLite file stores everything: text, 384-dim vector embeddings, JSON metadata, access tracking. Copy it, back it up, or delete it.
- **No external services** — No OpenAI API calls for memory operations. No cloud vector DB. Embedding model ships with the binary.
- **Hybrid search in milliseconds** — FTS5 full-text and cosine vector search fused with Reciprocal Rank Fusion. Text queries auto-vectorize. No manual `--vector` flag.
- **Agents that don't bloat** — Cosine similarity deduplication prevents your agent from accumulating thousands of near-duplicate memories.
- **Memories that matter surface first** — Decay scoring prioritizes frequently-accessed recent knowledge; stale memories fade out automatically.

---

## Install

Requires Rust toolchain, Python 3.9+, and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/archit15singh/memori.git
cd memori/memori-python && uv tool install --from . memori
```

First build compiles the Rust core with bundled SQLite and fastembed (~2–3 minutes). Subsequent runs start in milliseconds.

For the full walkthrough — verification steps, troubleshooting, dashboard tour — see **[docs/install.md](docs/install.md)**.

---

## Claude Code setup

One command writes a behavioral snippet that teaches Claude Code when and how to use memori:

```bash
cd ~ && memori setup          # writes snippet to ~/.claude/tools/memori/SNIPPET.md
memori setup --show           # preview before writing
memori setup --undo           # clean removal
```

After setup, Claude Code will:
- Load relevant context at session start (`memori context "<topic>"`)
- Store debugging root causes after fixing non-obvious bugs
- Store architecture decisions with alternatives considered
- Capture tool preferences and workflow choices
- Search past knowledge before deep-diving into unfamiliar code
- Update stale memories, purge scratch notes, backfill embeddings autonomously

---

## Demo

### Store memories with auto-embedding and dedup

```bash
$ memori store "FTS5 hyphens crash MATCH because - is the NOT operator. Fix: quote each token." \
    --meta '{"type": "debugging", "topic": "sqlite"}'
Stored: b338b67f-b40b-4243-9219-2a2375e3d249

$ memori store "Chose SQLite over Postgres for zero-config portability." \
    --meta '{"type": "decision", "topic": "architecture"}' --json
{"id": "6bf65b6f-dece-4be9-9517-7db7bf24dce7", "status": "created"}
```

Storing similar content of the same type auto-deduplicates — updates the existing memory instead of creating a duplicate.

### Hybrid search (FTS5 + vector, auto-vectorized)

```bash
$ memori search --text "sqlite" --limit 3
6bf65b6f [0.0329] Chose SQLite over Postgres for zero-config portability.  meta={"type": "decision"}
b338b67f [0.0304] FTS5 hyphens crash MATCH because - is the NOT operator.  meta={"type": "debugging"}

$ memori search --text "sqlite" --limit 1 --json
[
  {
    "id": "6bf65b6f-dece-4be9-9517-7db7bf24dce7",
    "content": "Chose SQLite over Postgres for zero-config portability.",
    "score": 0.0328,
    "metadata": {"topic": "architecture", "type": "decision"},
    "created_at": 1772183755.758478,
    "access_count": 0
  }
]
```

`--json` and `--raw` (compact single-line JSON) work before or after the subcommand — agents can compose them freely in pipes.

### Session start: context in one call

```bash
$ memori context "sqlite architecture" --limit 3
## Relevant Memories: "sqlite architecture"

- 6bf65b6f [0.0329] Chose SQLite over Postgres for zero-config portability.
- b338b67f [0.0304] FTS5 hyphens crash MATCH because - is the NOT operator.

## Recent Memories (by last update)

- 6bf65b6f [decision] Chose SQLite over Postgres...
- b338b67f [debugging] FTS5 hyphens crash MATCH...

## Frequently Accessed

- 6bf65b6f (12 hits) Chose SQLite over Postgres...

## Stale Memories (30+ days, never accessed)

- a1c2d3e4 WAL mode enables concurrent reads...

## Stats

Total: 12 memories
Types: debugging: 4, decision: 4, architecture: 2, fact: 1, preference: 1
```

Use `--compact` for a flat JSON payload that saves tokens in agent pipelines.

### Prefix IDs

All commands accept short prefixes (6+ chars):

```bash
$ memori get b338b67f                           # 8-char prefix
$ memori update b338b6 --content "new text"     # 6-char prefix
$ memori delete b338b67f --json
{"id": "b338b67f-b40b-4243-9219-2a2375e3d249", "status": "deleted"}
```

### Find related memories

```bash
$ memori related b338b67f --limit 3
6bf65b6f [0.8234] Chose SQLite over Postgres for zero-config portability.  meta={"type": "decision"}
a1c2d3e4 [0.4521] WAL mode enables concurrent reads with single writer.  meta={"type": "architecture"}
```

### Tag and filter

```bash
$ memori tag b338b67f verified=true severity=high count=3
Tagged b338b67f: {'count': 3, 'severity': 'high', 'topic': 'sqlite', 'type': 'debugging', 'verified': True}

$ memori search --filter '{"type": "debugging", "verified": true}'
```

Tag values auto-coerce: `true`/`false` → bool, `42` → int, `3.14` → float, else string.

### Date filters

```bash
$ memori search --text "kafka" --after 2026-02-01 --before 2026-03-01
$ memori list --type debugging --after 2026-01-01 --sort updated
```

### Database stats and maintenance

```bash
$ memori stats
Database:  ~/.claude/memori.db
Memories:  12
File size: 72.0 KB
Embedded:  12/12 (100%)
Types:
  debugging: 4
  decision: 4
  architecture: 2
  preference: 1
  fact: 1

$ memori gc
Compacted: 72.0 KB -> 60.0 KB (saved 12.0 KB)

$ memori embed             # backfill embeddings on memories with NULL vectors
$ memori embed --batch-size 100
```

### Export / import (lossless round-trip)

```bash
$ memori export > backup.jsonl                          # preserves access stats
$ memori import < backup.jsonl                          # preserves IDs + access stats
$ memori import --new-ids < backup.jsonl                # fresh UUIDs
$ memori export --include-vectors > full-backup.jsonl
```

### Web dashboard

```bash
$ memori ui                 # opens http://localhost:8899
$ memori ui --port 9000
$ memori ui --no-open       # start without auto-opening browser
```

Dark-themed dashboard with: memory list (search, type filter, sort, date range), types donut chart, creation timeline scatter plot, memory detail panel, and a D3 force-directed connection graph (2-hop traversal from any memory). Read-only — browsing does not inflate access counts. Charts require internet (Chart.js + D3 from CDN); memory list works offline.

---

## Why Memori

The hard problem for AI agents isn't *storing* memories — it's *finding the right one* when you need it. Keyword search misses semantic matches. Pure vector search misses exact terms. Memori solves this with three design choices that are unusual in the space:

### 1. Hybrid search with Reciprocal Rank Fusion

Memori runs FTS5 full-text (BM25 scoring) and cosine vector similarity independently, then fuses results using [Reciprocal Rank Fusion](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf) (k=60) — a rank-based method that avoids the normalization problem between BM25 (negative floats) and cosine similarity (0..1). Text queries auto-vectorize; no `--vector` flag needed.

| Query | Mode | How it works |
|-------|------|-------------|
| `--text "..."` | Hybrid (auto) | Auto-embeds → runs FTS5 + cosine → RRF fusion |
| `--text "..." --text-only` | FTS5 only | Faster, for exact term matching |
| `--vector [...]` | Vector only | Brute-force cosine similarity |
| neither | Recent | Returns most recently updated memories |

### 2. Access-weighted decay scoring

Every memory carries `access_count` and `last_accessed`. Search results are boosted by usage:

```
final_score = base_score × boost × decay

boost = 1 + 0.1 × ln(1 + access_count)   # logarithmic, sublinear
decay = exp(−0.01 × days_since_last_access) # ~69-day half-life
```

Frequently-accessed memories surface first; stale ones fade. New memories carry no decay penalty until accessed.

### 3. Cosine-similarity deduplication

On insert, memori checks for existing memories of the same type with cosine similarity > 0.92 (configurable). A near-duplicate triggers an update instead of a new insert. Agents that store aggressively don't accumulate hundreds of redundant memories over time.

### Zero LLM dependency

Unlike Mem0 (requires LLM API calls to extract and structure memories) or Graphiti (knowledge graph over LLM), memori uses fastembed's AllMiniLM-L6-V2 (384-dim, ~9ms/memory on M4 Pro) — no API keys, no network, no rate limits. The model ships with the binary and is cached locally after the first use.

### Comparison

| | Memori | Mem0 | Engram | agent-recall |
|---|---|---|---|---|
| Storage | SQLite (single file) | Postgres + vector DB + graph DB | SQLite | SQLite |
| Embeddings | Built-in (fastembed) | External API | None | None |
| Search | Hybrid FTS5 + vector (RRF) | Vector only | FTS5 only | SQLite FTS |
| Deduplication | Cosine similarity (auto) | None | None | None |
| Decay scoring | Access + time | Access counter only | None | None |
| LLM dependency | None | Required | None | None |
| Config | Zero | Cloud service | File | File |

---

## Performance

> Benchmarked on Apple M4 Pro (14-core, 48 GB RAM), macOS Sequoia. Latency benchmarks use in-memory SQLite — no disk I/O variance. Measured with [Criterion.rs](https://github.com/bheisler/criterion.rs) on pre-computed 384-dim vectors (embedding latency excluded except in dedicated embed benchmarks).

### Search & CRUD latency

| Operation | 1K | 10K | 100K | 500K |
|---|---|---|---|---|
| get (UUID) | 43 µs | 60 µs | 183 µs | 47 µs |
| get (prefix†) | 65 µs | 257 µs | 2.15 ms | 12.5 ms |
| insert (no embed) | 83 µs | 95 µs | 177 µs | 45 µs |
| count | 636 ns | 1.1 µs | 11.1 µs | 71 µs |
| list (limit 20) | 1.05 ms | 11.5 ms | 123 ms | 621 ms |
| text search (FTS5) | 65 µs | 171 µs | 1.49 ms | 7.5 ms |
| vector search | 1.00 ms | 14.7 ms | 172 ms | 904 ms |
| hybrid search (RRF) | 1.12 ms | 14.0 ms | 162 ms | 913 ms |
| filtered vector search | 154 µs | 1.54 ms | 22.9 ms | 130 ms |

*†8-char prefixes collide above ~100K UUIDs (birthday paradox on 16^8); use 12-char at 500K scale.*

### Storage and write throughput

| Memories | DB Size | Per Memory | Writes/sec |
|---|---|---|---|
| 1,000 | 4.3 MB | 4.4 KB | 8,100 |
| 10,000 | 42.5 MB | 4.4 KB | 7,200 |
| 100,000 | 424.6 MB | 4.3 KB | 6,400 |
| 500,000 | 2.07 GB | 4.3 KB | 5,700 |
| 1,000,000 | 4.15 GB | 4.3 KB | 4,200 |

*Each memory: ~100 words + 384-dim embedding vector + JSON metadata. Measured on file-backed SQLite after VACUUM. Write throughput includes FTS5 indexing.*

### Single-op latency

| Operation | Latency |
|---|---|
| cosine_similarity (384-dim) | 213 ns |
| vec_to_blob / blob_to_vec | <40 ns |
| embed_text (AllMiniLM-L6-V2) | 9 ms |
| embed_batch (10 texts) | 133 ms |
| embed_batch (100 texts) | 963 ms |
| insert + auto-embed | 18 ms end-to-end |

<details>
<summary>Reproduce benchmarks</summary>

```bash
# Run all Rust benchmarks (~30 min with 500K scale)
cargo bench -p memori-core

# Individual benchmark groups
cargo bench -p memori-core --bench search_bench    # search at 1K/10K/100K/500K
cargo bench -p memori-core --bench crud_bench      # CRUD at 1K/10K/100K/500K
cargo bench -p memori-core --bench vector_ops_bench
cargo bench -p memori-core --bench embed_bench     # requires embeddings feature
cargo bench -p memori-core --bench memory_bench    # file size + throughput (1K-1M, ~10 min)

# Parse criterion output into a markdown table
python3 scripts/bench-table.py

# CLI-level timing (requires hyperfine)
bash scripts/bench-cli.sh

# Open HTML report
open target/criterion/report/index.html
```

</details>

---

## How it works

### Storage

Single SQLite file with WAL journaling. One table with 8 columns: `id` (UUID v4), `content`, `vector` (f32 BLOB), `metadata` (JSON), `created_at`, `updated_at`, `last_accessed`, `access_count`. An FTS5 external-content virtual table indexes `content || ' ' || metadata` via sync triggers — full-text search covers both memory text and metadata values, with no text duplication.

Schema migrations via `PRAGMA user_version` (v0–v3): FTS5 virtual table + triggers → access tracking columns → expression index on `json_extract(metadata, '$.type')` for fast type-filtered queries.

### Embeddings

[AllMiniLM-L6-V2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) via fastembed — 384 dimensions, ~9ms per memory on M4 Pro. Stored as raw f32 BLOBs (~1.5KB each). Lazy OnceLock singleton: model loads on first use, cached in-process thereafter. Model files cached to `~/.fastembed_cache/` on first run (~90MB download).

On metadata update, the vector is re-embedded from `content + scalar metadata values` — so tagging a memory with `topic=kafka` shifts its vector toward the topic, making it findable by semantic search without touching the content text.

### Deduplication

On insert, if dedup is enabled (default threshold: 0.92), memori scans same-type memories, finds the best cosine similarity match, and updates instead of inserting if above threshold. O(N) per type bucket — fast for typical agent memory counts.

Note: tagging or updating metadata re-embeds the vector, which can shift it enough that identical content stored later may not dedup against the original. This is by design — the vectors represent different information after tagging.

### Prefix ID resolution

All ID-based commands accept 6+ character prefixes. Resolution uses `WHERE id LIKE prefix%` on the UUID primary key — a B-tree range scan, not a full table scan. Returns an error on ambiguous matches.

---

## Architecture

```
memori-core/  (Rust library, v0.6.0)
  lib.rs        Memori facade — prefix-resolving API over storage + search
  types.rs      Memory, SearchQuery, InsertResult, MemoriError, SortField
  schema.rs     SQLite DDL, migration versions v0–v3 (PRAGMA user_version)
  storage.rs    CRUD, prefix resolution, list, bulk ops, dedup, metadata merge
  search.rs     Vector/text/hybrid/recent search, RRF fusion, decay scoring
  embed.rs      fastembed AllMiniLM-L6-V2 (lazy singleton, feature-gated)
  util.rs       cosine_similarity, vec<->blob (unsafe pointer casts, f32 platform-native)

memori-python/  (PyO3 bindings + CLI, v0.6.0)
  src/lib.rs          PyMemori class (Mutex<Memori>, GIL release on search/insert/embed)
  python/memori_cli/  Argparse CLI (18 subcommands, --json/--raw on all)
    data/             claude_snippet.md, dashboard.html (single-file web UI)
```

**Key design decisions:**

- **Single SQLite file + WAL** — portability over throughput. One `.db` file, copyable anywhere.
- **Brute-force vector search** — O(N) cosine similarity. Adequate to ~100K memories at 384 dims. `vector_search()` is the sole hot path, isolated for drop-in HNSW replacement.
- **FTS5 external-content table** — no text duplication. Triggers keep the inverted index in sync with the base table.
- **RRF hybrid fusion (k=60)** — rank-based, not score-based. Sidesteps BM25/cosine normalization incompatibility.
- **Vectors stripped by default** — 10KB per memory reduced to ~500 bytes in output. Opt-in via `--include-vectors`.
- **`Mutex<Memori>` in PyO3** — `rusqlite::Connection` is `!Sync`. `py.allow_threads()` releases the GIL during search, insert, embed, and related lookups.

---

## CLI reference

```
memori [--db PATH] [--json | --raw] [--version] <command> [options]
```

Global options work before or after the subcommand.

### store

```bash
memori store "memory text" --meta '{"type": "debugging"}'
memori store "text" --no-embed              # skip auto-embedding
memori store "text" --no-dedup             # skip dedup check
memori store "text" --dedup-threshold 0.95 # stricter dedup (default: 0.92)
memori store "text" --vector '[1.0, 0.0, ...]'  # explicit embedding
```

### search

```bash
memori search --text "query"              # hybrid (FTS5 + vector, auto-vectorized)
memori search --text "query" --text-only  # FTS5-only (faster, exact matches)
memori search --vector '[...]'            # pure vector search
memori search --filter '{"type": "debugging"}'
memori search --text "query" --before 2026-03-01 --after 2026-01-01
memori search --text "query" --limit 20
memori search --text "query" --include-vectors
```

### context

```bash
memori context "topic"                # relevant + recent + frequent + stale + stats
memori context "topic" --limit 5
memori context "topic" --project app  # scoped to metadata.project
memori context "topic" --compact      # minimal flat JSON for agent pipelines
```

### get / update / tag / delete

```bash
memori get <id>                              # full ID or prefix (6+ chars)
memori get <id> --include-vectors

memori update <id> --content "new text"
memori update <id> --meta '{"key": "value"}'           # merged by default
memori update <id> --meta '{"key": "value"}' --replace # replace all metadata

memori tag <id> verified=true topic=fts5 count=42      # auto-types: bool, str, int

memori delete <id>
```

### related

```bash
memori related <id>            # find similar memories by vector
memori related <id> --limit 10
```

### list

```bash
memori list                              # default: 20, sorted by created_at DESC
memori list --type debugging
memori list --sort count --limit 10      # most frequently accessed
memori list --sort updated               # recently modified
memori list --sort accessed              # recently accessed
memori list --offset 20 --limit 20      # pagination
memori list --before 2026-01-01 --after 2025-06-01
```

### maintenance

```bash
memori stats                             # DB size, types, embedding coverage
memori count                             # quick count
memori embed                             # backfill embeddings for old memories
memori embed --batch-size 100
memori gc                                # compact database (SQLite VACUUM)
memori purge --type temporary            # preview what would be deleted
memori purge --type temporary --confirm  # actually delete
memori purge --before 2025-01-01 --confirm
```

### export / import

```bash
memori export > backup.jsonl
memori export --include-vectors > full-backup.jsonl
memori import < backup.jsonl
memori import --new-ids < backup.jsonl
```

### dashboard

```bash
memori ui                    # open web dashboard on port 8899
memori ui --port 9000
memori ui --no-open          # start server without auto-opening browser
```

---

## Python API

```python
from memori import PyMemori

db = PyMemori("memories.db")

# Store (auto-embeds; Python API default is no dedup — pass explicitly)
result = db.insert("user prefers dark mode", metadata={"type": "preference"})
# result = {"id": "abc-123...", "action": "created"}

result = db.insert("similar text", dedup_threshold=0.92)
# result = {"id": "abc-123...", "action": "deduplicated"}

result = db.insert("no vector needed", no_embed=True)

# Search (hybrid by default — auto-vectorizes text queries)
results = db.search(text="dark mode")
results = db.search(text="dark mode", text_only=True)  # FTS5-only
results = db.search(vector=[1.0, 0.0, ...], limit=5)
results = db.search(filter={"type": "preference"})
results = db.search(text="query", before=1772000000.0, after=1771000000.0)

# Get (prefix IDs supported; bumps access_count)
mem = db.get("abc123")
mem = db.get_readonly("abc123")  # read without bumping access stats

# Related
similar = db.related("abc123", limit=5)

# Update (metadata merged by default)
db.update("abc123", content="updated text")
db.update("abc123", metadata={"verified": True})
db.update("abc123", metadata={"new": "only"}, merge_metadata=False)

# Delete / list
db.delete("abc123")
recent = db.list(sort="updated", limit=10)
popular = db.list(sort="count", limit=10)
typed = db.list(type_filter="debugging", limit=20)
paged = db.list(limit=20, offset=40)

# Embeddings
db.backfill_embeddings(batch_size=50)
stats = db.embedding_stats()   # {"embedded": 10, "total": 12}
vec = db.embed("some text")    # raw 384-dim vector

# Maintenance
db.vacuum()
dist = db.type_distribution()  # {"preference": 3, "fact": 1}
db.delete_before(timestamp)
db.delete_by_type("temporary")
```

---

## Testing

~195 tests across three layers — all real SQLite, no mocking:

- **Rust integration** (`memori-core/tests/integration_test.rs`): 63 tests using in-memory SQLite via `open_temp()`. Covers CRUD, dedup, all four search modes, decay scoring, prefix resolution, embedding backfill, export/import.
- **Python API** (`memori-python/tests/test_memori.py`): 37 pytest tests via `tmp_path` fixture. Covers PyMemori bindings end-to-end.
- **CLI** (`memori-python/tests/test_cli.py`): ~95 subprocess-based tests. Full command matrix: all 18 subcommands, output modes, error cases, date filtering, dedup behavior, typed tag coercion, purge AND logic.

```bash
cargo test -p memori-core
cd memori-python && maturin develop && pytest tests/test_memori.py tests/test_cli.py -v
```

---

## Non-obvious behaviors

- **Dedup drift after tagging** — Tagging re-embeds the vector (content + scalar metadata values), shifting it. Storing identical content later may not dedup against a heavily-tagged original because the vectors diverged. FTS5 still finds both.
- **Purge uses AND logic** — `--before` and `--type` together delete only the intersection.
- **Python API vs CLI dedup** — CLI defaults to 0.92 dedup. Python API defaults to `None` (no dedup). Pass `dedup_threshold=0.92` explicitly in the Python API.
- **FTS5 vs vector embedding asymmetry** — FTS5 indexes `content || ' ' || COALESCE(metadata, '')` (raw JSON). Vector embedding uses `content + top-level scalar metadata values`. FTS5 can match JSON keys; vector search cannot.
- **Prefix collisions** — 8-char prefixes collide above ~100K UUIDs (birthday paradox on 16^8 space). Use 12-char prefixes at scale.
- **Exit codes** — 0 success, 1 not found, 2 user input error. `--json` errors go to stderr; successes to stdout.

---

## License

MIT
