# Memori

Persistent memory for AI coding agents. SQLite + FTS5 + vector search in a single binary.

Memori gives Claude Code (and other AI agents) the ability to remember decisions, debugging lessons, architecture notes, and user preferences across sessions -- so every session starts smarter than the last.

## Install

Requires Rust toolchain and Python 3.9+.

```bash
# Clone and install
git clone https://github.com/archit-15dev/memori.git
cd memori/memori-python
uv tool install --from . memori

# Or with pip/pipx
pip install maturin
cd memori/memori-python
maturin develop
```

## Claude Code Setup

One command adds a behavioral snippet to your CLAUDE.md that teaches Claude Code when and how to use memori:

```bash
memori setup          # adds snippet to CLAUDE.md
memori setup --show   # preview what gets written
memori setup --undo   # clean removal
```

After setup, Claude Code will automatically:
- Load relevant context at session start (`memori context "<topic>"`)
- Store debugging lessons after fixing non-obvious bugs
- Store architecture decisions with rationale
- Capture user preferences
- Search past knowledge before deep research
- Self-maintain memory quality (update stale entries, prune scratch notes)

## Demo

### Store memories with auto-embeddings and dedup

```bash
$ memori store "FTS5 hyphens crash MATCH because - is the NOT operator. Fix: quote each token." \
    --meta '{"type": "debugging", "topic": "sqlite"}'
Stored: b338b67f-b40b-4243-9219-2a2375e3d249

$ memori store "Chose SQLite over Postgres for zero-config portability." \
    --meta '{"type": "decision", "topic": "architecture"}' --json
{"id": "6bf65b6f-dece-4be9-9517-7db7bf24dce7", "status": "created"}
```

Storing similar content of the same type auto-deduplicates (updates the existing memory instead of creating a duplicate).

### Hybrid search (FTS5 + vector)

Text searches auto-vectorize into hybrid search for best results. No manual `--vector` needed:

```bash
$ memori search --text "sqlite" --limit 3
6bf65b6f [0.0329] Chose SQLite over Postgres for zero-config portability.  meta={"type": "decision"}
b338b67f [0.0304] FTS5 hyphens crash MATCH because - is the NOT operator.  meta={"type": "debugging"}
```

Machine-readable JSON (vectors stripped by default to save tokens):

```bash
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

`--json` and `--raw` work in both positions -- before or after the subcommand:

```bash
$ memori --json search --text "sqlite"     # before subcommand
$ memori search --text "sqlite" --json     # after subcommand (same result)
$ memori search --text "sqlite" --raw      # compact single-line JSON
```

### Prefix IDs

All commands that take an ID accept short prefixes (6+ chars recommended):

```bash
$ memori get b338b67f                 # 8-char prefix
$ memori update b338b6 --content "new text"   # 6-char prefix
$ memori delete b338b67f --json
{"id": "b338b67f-b40b-4243-9219-2a2375e3d249", "status": "deleted"}
```

Mutation output always shows the resolved full UUID, even when you pass a prefix.

### Find related memories

Discover memories similar to one you already have:

```bash
$ memori related b338b67f --limit 3
6bf65b6f [0.8234] Chose SQLite over Postgres for zero-config portability.  meta={"type": "decision"}
a1c2d3e4 [0.4521] WAL mode enables concurrent reads with single writer.  meta={"type": "architecture"}
```

### Tag memories with key=value pairs

```bash
$ memori tag b338b67f verified=true severity=high
Tagged b338b67f-b40b-4243-9219-2a2375e3d249: {'severity': 'high', 'topic': 'sqlite', 'type': 'debugging', 'verified': 'true'}
```

### Context loading (one call for session start)

Loads relevant matches + recent memories + frequently accessed + stale candidates + type stats:

```bash
$ memori context "sqlite architecture" --limit 3
## Relevant Memories: "sqlite architecture"

- 6bf65b6f [0.0329] Chose SQLite over Postgres for zero-config portability.
- b338b67f [0.0304] FTS5 hyphens crash MATCH...

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

### Date filters on search and list

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

$ memori embed
All 12 memories already have embeddings.
```

### Export / Import (lossless round-trip)

Exports preserve access stats (last_accessed, access_count) for full fidelity:

```bash
$ memori export > backup.jsonl
$ memori import < backup.jsonl        # preserves IDs + access stats
$ memori import --new-ids < backup.jsonl  # fresh UUIDs
```

## CLI Reference

```
memori [--db PATH] [--json | --raw] [--version] <command> [options]
```

Global options work before or after the subcommand.

### Store

```bash
memori store "memory text" --meta '{"type": "debugging"}'
memori store "text" --vector '[1.0, 0.0, ...]'  # explicit embedding
memori store "text" --no-embed          # skip auto-embedding
memori store "text" --no-dedup          # skip dedup check
memori store "text" --dedup-threshold 0.95  # stricter dedup (default: 0.92)
```

### Search

```bash
memori search --text "query"            # hybrid search (FTS5 + vector)
memori search --text "query" --text-only  # FTS5-only (faster, exact matches)
memori search --vector '[1.0, 0.0, ...]'  # pure vector search
memori search --filter '{"type": "debugging"}'
memori search --text "query" --before 2026-03-01 --after 2026-01-01
memori search --text "query" --limit 20
memori search --text "query" --include-vectors  # include embedding data
```

### Context

```bash
memori context "topic"                  # load relevant + recent + stats
memori context "topic" --limit 5        # fewer relevant matches
memori context "topic" --project myapp  # scoped to metadata.project
```

### Get / Update / Tag / Delete

```bash
memori get <id>                         # full ID or prefix (6+ chars)
memori get <id> --include-vectors

memori update <id> --content "new text"
memori update <id> --meta '{"key": "value"}'  # merged by default
memori update <id> --meta '{"key": "value"}' --replace  # replace all metadata
memori update <id> --vector '[1.0, 0.0, ...]'  # explicit vector replacement

memori tag <id> verified=true topic=fts5

memori delete <id>
```

### Related

```bash
memori related <id>                     # find similar memories by vector
memori related <id> --limit 10
```

### List

```bash
memori list                             # default: 20, sorted by created_at
memori list --type debugging            # filter by metadata type
memori list --sort count --limit 10     # most frequently accessed
memori list --sort updated              # recently modified
memori list --sort accessed             # recently accessed
memori list --offset 20 --limit 20     # pagination
memori list --before 2026-01-01 --after 2025-06-01
```

### Maintenance

```bash
memori stats                            # DB size, types, embedding coverage
memori count                            # quick count
memori embed                            # backfill embeddings for old memories
memori embed --batch-size 100           # larger batches
memori gc                               # compact database (SQLite VACUUM)
memori purge --type temporary           # preview what would be deleted
memori purge --type temporary --confirm # actually delete
memori purge --before 2025-01-01 --confirm
```

### Export / Import

```bash
memori export > backup.jsonl
memori export --include-vectors > full-backup.jsonl
memori import < backup.jsonl
memori import --new-ids < backup.jsonl
```

### Dashboard

```bash
memori ui                    # open web dashboard on port 8899
memori ui --port 9000        # custom port
memori ui --no-open          # don't auto-open browser
```

Browse, search, and visualize your memory database in a dark-themed web dashboard. Read-only -- UI browsing does not inflate access counts. Features: search with 300ms debounce, type/sort/date filters, interactive type donut chart, timeline scatter plot (capped at 500 memories), memory detail panel, and D3 force-directed connection graph (2-hop traversal from any memory). Charts require internet (Chart.js and D3 loaded from CDN); the memory list works offline.

### Setup

```bash
memori setup          # inject snippet into CLAUDE.md
memori setup --show   # preview snippet
memori setup --undo   # remove snippet
```

## Python API

```python
from memori import PyMemori

db = PyMemori("memories.db")

# Store (auto-embeds, auto-dedup by default)
result = db.insert("user prefers dark mode", metadata={"type": "preference"})
# result = {"id": "abc-123...", "action": "created"}

result = db.insert("similar text", dedup_threshold=0.92)  # must pass explicitly; default is None (no dedup)
# result = {"id": "abc-123...", "action": "deduplicated"}

result = db.insert("no vector needed", no_embed=True)

# Search (hybrid by default -- auto-vectorizes text queries)
results = db.search(text="dark mode")
results = db.search(text="dark mode", text_only=True)  # FTS5-only
results = db.search(vector=[1.0, 0.0, ...], limit=5)
results = db.search(filter={"type": "preference"})
results = db.search(text="query", before=1772000000.0, after=1771000000.0)

# Get (supports prefix IDs, bumps access_count)
mem = db.get("abc123")  # 6+ char prefix
mem = db.get("abc12345-full-uuid-here")

# Get without bumping access_count (read-only, used by dashboard)
mem = db.get_readonly("abc123")

# Related (find similar by vector)
similar = db.related("abc123", limit=5)

# Update (metadata merged by default)
db.update("abc123", content="updated text")
db.update("abc123", metadata={"verified": True})
db.update("abc123", metadata={"new": "only"}, merge_metadata=False)  # replace

# Delete
db.delete("abc123")

# List with sorting and pagination
all_memories = db.list(limit=50)
recent = db.list(sort="updated", limit=10)
popular = db.list(sort="count", limit=10)
typed = db.list(type_filter="debugging", limit=20)
paged = db.list(limit=20, offset=40)
dated = db.list(before=1772000000.0, after=1771000000.0)

# Bulk operations
dist = db.type_distribution()            # {"preference": 3, "fact": 1}
db.delete_before(timestamp)              # bulk delete by age
db.delete_by_type("temporary")           # bulk delete by type

# Import/export helpers
db.insert_with_id("custom-id", "content", created_at=ts, updated_at=ts)
db.set_access_stats("id", last_accessed=ts, access_count=5)

# Embeddings
db.backfill_embeddings(batch_size=50)
stats = db.embedding_stats()             # {"embedded": 10, "total": 12}
vec = db.embed("some text")              # raw 384-dim embedding vector

# Maintenance
db.vacuum()
```

## Performance

> **Benchmarked on**: Apple M4 Pro (14-core CPU, 48 GB RAM), macOS Sequoia.

Latency benchmarks use in-memory SQLite with deterministic seeding (no disk I/O variance). Measured with [Criterion.rs](https://github.com/bheisler/criterion.rs) on pre-computed 384-dim vectors -- embedding model latency excluded except in dedicated embedding benchmarks.

### Search & CRUD Latency

| Operation | 1,000 | 10,000 | 100,000 | 500,000 |
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

*†Prefix = 8 chars at ≤100K, 12 chars at 500K (8-char prefixes collide above ~100K UUIDs via birthday paradox).*

### Memory Efficiency

Measured with file-backed SQLite (realistic storage), scaling from 1K to 1M memories.

| Memories | DB Size | Per-Memory | Write Throughput |
|---|---|---|---|
| 1,000 | 4.3 MB | 4.4 KB | 8,100/s |
| 10,000 | 42.5 MB | 4.4 KB | 7,200/s |
| 100,000 | 424.6 MB | 4.3 KB | 6,400/s |
| 500,000 | 2.07 GB | 4.3 KB | 5,700/s |
| 1,000,000 | 4.15 GB | 4.3 KB | 4,200/s |

*Each memory: ~100 words of content + 384-dim embedding vector + JSON metadata. DB file measured after VACUUM. Write throughput = inserts/sec including FTS5 indexing. SQLite reads pages on demand -- the full DB is never loaded into RAM.*

### Single-Op Latency

| Operation | Latency |
|---|---|
| cosine_similarity (384-dim) | 213 ns |
| vec_to_blob / blob_to_vec | <40 ns |
| embed_text (AllMiniLM-L6-V2) | 9 ms |
| embed_batch (10 texts) | 133 ms |
| embed_batch (100 texts) | 963 ms |
| insert + auto-embed | 18 ms |

<details>
<summary>Reproduce these benchmarks</summary>

```bash
# Run all Rust benchmarks (~30 min with 500K scale)
cargo bench -p memori-core

# Run specific benchmark group
cargo bench -p memori-core --bench search_bench    # search at 1K/10K/100K/500K
cargo bench -p memori-core --bench crud_bench      # CRUD at 1K/10K/100K/500K
cargo bench -p memori-core --bench vector_ops_bench
cargo bench -p memori-core --bench embed_bench     # requires embeddings feature
cargo bench -p memori-core --bench memory_bench    # file size + write throughput (1K-1M)

# Generate markdown table from criterion output
python3 scripts/bench-table.py

# CLI-level timing (requires: brew install hyperfine)
bash scripts/bench-cli.sh

# Open HTML reports
open target/criterion/report/index.html
```

</details>

## How It Works

### Storage

Single SQLite file with WAL journaling. Memories are stored in one table with 8 columns: `id` (UUID v4), `content`, `vector` (BLOB), `metadata` (JSON), `created_at`, `updated_at`, `last_accessed`, `access_count`. An FTS5 external-content virtual table indexes `content || ' ' || metadata` with sync triggers, so full-text search covers both memory text and metadata values.

### Embeddings

Auto-generated on insert via [AllMiniLM-L6-V2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) (384 dimensions, ~9ms per memory on Apple M4 Pro). Stored as raw f32 BLOBs (~1.5KB each). Feature-gated behind `embeddings` (default on). Model files cached to `.fastembed_cache/` on first use.

### Search Algorithm

Four modes based on query parameters:

| Query | Mode | How it works |
|-------|------|-------------|
| `text + vector` | Hybrid (RRF) | Runs both FTS5 and cosine independently, fuses via Reciprocal Rank Fusion (K=60) |
| `text` only | Hybrid (auto) | Auto-embeds the query text, then runs hybrid search |
| `text` + `text_only` | Text (FTS5) | Pure FTS5 search, no vectorization -- faster for exact term matching |
| `vector` only | Vector | Brute-force cosine similarity against all stored vectors |
| neither | Recent | Returns most recently updated memories |

**Hybrid search** runs FTS5 (BM25 scoring) and cosine similarity independently at 3x the requested limit, then fuses results using [Reciprocal Rank Fusion](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf) -- a rank-based method that avoids the score normalization problem between BM25 (negative floats) and cosine (0..1).

FTS5 queries are sanitized by quoting each token to prevent operator injection (hyphens, colons, asterisks).

### Decay Scoring

Search results are boosted by usage patterns:

```
final_score = base_score * boost * decay
```

- **boost** = `1 + 0.1 * ln(1 + access_count)` -- logarithmic, sublinear growth (10 accesses = 1.24x, 100 accesses = 1.46x)
- **decay** = `exp(-0.01 * days_since_last_access)` -- exponential with ~69-day half-life
- Never-accessed memories get no decay penalty (decay = 1.0)

This surfaces frequently-used memories while gradually deprioritizing forgotten ones.

### Prefix ID Resolution

All ID-based commands accept short prefixes (6+ chars recommended). Resolution uses `WHERE id LIKE prefix%` on the TEXT primary key (B-tree range scan, not full table scan). Returns an error if the prefix is ambiguous (matches 2+ memories).

### Deduplication

On insert, if a vector is available and dedup is enabled (default threshold: 0.92 cosine similarity), memori scans same-type memories and updates the best match instead of creating a duplicate. O(N) per insert within the type bucket.

## Architecture

```
memori-core/  (Rust library crate, v0.5.0)
  lib.rs        Memori facade -- prefix-resolving API over storage + search
  types.rs      Memory, SearchQuery, InsertResult, MemoriError, SortField
  schema.rs     SQLite DDL, 3 migration versions (PRAGMA user_version)
  storage.rs    CRUD, prefix resolution, list, bulk ops, dedup, metadata merge
  search.rs     Vector/text/hybrid search, RRF fusion, decay scoring
  embed.rs      fastembed AllMiniLM-L6-V2 (lazy singleton, feature-gated)
  util.rs       cosine_similarity, vec<->blob conversion

memori-python/  (PyO3 bindings + CLI, v0.5.1)
  src/lib.rs    PyMemori class (Mutex<Memori>, GIL release on search)
  python/
    memori/     Re-exports PyMemori from native .so (stable ABI, py39+)
    memori_cli/ Argparse CLI (18 subcommands, --json/--raw on all)
      data/     claude_snippet.md, dashboard.html (web UI)
```

### Key design decisions

- **Single SQLite file + WAL** -- portability over throughput. The entire DB is one `.db` file.
- **Brute-force vector search** -- O(N) cosine similarity. Adequate to ~100K memories at 384 dims. The `vector_search()` function is the sole hot path, designed for drop-in HNSW replacement when needed.
- **FTS5 external-content table** -- no text duplication. Sync triggers keep the inverted index consistent with the base table.
- **RRF hybrid fusion (K=60)** -- rank-based, not score-based. Sidesteps the normalization problem between cosine and BM25.
- **Vectors stripped by default** -- 10KB per memory reduced to ~500 bytes in output. Opt-in via `--include-vectors`.
- **Agent-as-user introspection** -- after each release, the AI agent uses the tool on real data and reports honestly on the experience. Bug fixes in v0.5.1 were found this way.

## License

MIT
