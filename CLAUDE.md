# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Test Commands

```bash
# Rust core -- build and test
cargo build --workspace
cargo test -p memori-core

# Python bindings -- build (requires venv with maturin)
cd memori-python && maturin develop

# Python tests
pytest memori-python/tests/test_memori.py -v

# Install as CLI tool
cd memori-python && uv tool install --from . memori

# Benchmarks (criterion + memory)
cargo bench -p memori-core                          # all benchmarks (~30 min with 500K)
cargo bench -p memori-core --bench vector_ops_bench  # micro-benchmarks only (~30s)
cargo bench -p memori-core --bench crud_bench        # CRUD at 1K/10K/100K/500K
cargo bench -p memori-core --bench search_bench      # search at 1K/10K/100K/500K
cargo bench -p memori-core --bench embed_bench       # embedding model (slow)
cargo bench -p memori-core --bench memory_bench      # file size + throughput (1K-1M, ~10 min)
python3 scripts/bench-table.py                       # criterion JSON -> markdown table
bash scripts/bench-cli.sh                            # CLI-level timing (needs hyperfine)

# Full verification after changes
cargo test -p memori-core && cd memori-python && maturin develop && pytest tests/test_memori.py -v
```

No linter configuration exists. No CI/CD workflows are set up.

## Architecture

Memori is a persistent memory system for AI coding agents. Single-binary, SQLite-backed with FTS5 full-text search and vector search. Two Rust crates + a Python CLI layer:

```
User/Agent
    |
memori CLI (Python argparse, 18 subcommands)
    |
PyMemori (PyO3 bindings, Mutex<Memori>)
    |
Memori struct (lib.rs -- thin facade with prefix ID resolution)
    |
+-- storage.rs  CRUD, prefix resolution, list, dedup, metadata merge
+-- search.rs   4 search modes, RRF hybrid fusion, decay scoring
+-- embed.rs    fastembed AllMiniLM-L6-V2 (lazy OnceLock singleton)
+-- schema.rs   DDL, FTS5 virtual table, triggers, 3 migration versions
+-- types.rs    Memory, SearchQuery, MemoriError, SortField, InsertResult
+-- util.rs     cosine_similarity, vec<->blob conversion
```

**Key design choices:**
- Single SQLite file with WAL mode -- portability over throughput
- Brute-force vector search (adequate to ~100K vectors) -- only `search.rs::vector_search()` touches vectors, designed for drop-in HNSW replacement
- FTS5 external content table (`content=memories`) -- no text duplication, triggers in `schema.rs` keep FTS in sync
- RRF hybrid fusion (k=60) -- rank-based, not score-based, because cosine similarity and BM25 ranks are on incompatible scales
- `Mutex<Memori>` in Python bindings because `rusqlite::Connection` is `!Sync` and `py.allow_threads()` releases the GIL during search

**Schema migrations** are tracked via `PRAGMA user_version` (v0 through v3). Each migration is an `if version < N` block in `schema.rs::init_db()`. v0->1: FTS5 + metadata-aware triggers; v1->2: `last_accessed`/`access_count` columns; v2->3: expression index on `json_extract(metadata, '$.type')`.

## Non-Obvious Constraints

- **Vector BLOB format**: f32 arrays as raw bytes, platform-native byte order. `unsafe` pointer casts in `util.rs`
- **FTS5 triggers fire on rowid, not UUID `id`**: the JOIN in `text_search()` bridges this via `m.rowid = fts.rowid`
- **FTS5 delete syntax**: `INSERT INTO memories_fts(memories_fts, rowid, content) VALUES('delete', ...)` -- FTS5's documented removal mechanism
- **Metadata filter is flat equality only**: `build_filter_clause()` in `search.rs` converts JSON to `json_extract()` WHERE clauses -- no nested paths, no operators. Filter keys are validated by `is_valid_filter_key()` against `[a-zA-Z_][a-zA-Z0-9_]*` -- rejects nested paths and prevents SQL injection.
- **Prefix ID resolution**: `LIKE prefix%` on UUID primary key maps to a B-tree range scan. The facade in `lib.rs` wraps get/get_readonly/update/delete/touch/set_access_stats/related with prefix resolution. Note: 8-char hex prefixes collide above ~100K UUIDs (birthday paradox on 16^8 space); use longer prefixes at scale
- **Decay scoring**: logarithmic access boost + exponential time decay (~69 day half-life). `access_count == 0` guard prevents penalizing newly-stored memories
- **Dedup threshold**: cosine similarity > 0.92 between same-type memories triggers update instead of insert (strictly greater-than -- equality does not trigger dedup)
- **FTS5 vs vector embedding asymmetry**: FTS5 indexes `content || ' ' || COALESCE(metadata, '')` (raw JSON with keys/braces). Vector embedding uses `content + metadata_values_text()` (top-level scalar values only). On initial insert, auto-embed uses content only; on metadata update, re-embeds from `content + scalar metadata values`. FTS5 can match JSON keys, vector search cannot.
- **Hybrid search over-fetches**: RRF fusion retrieves `3 * limit` candidates from each sub-search before rank fusion and truncation.
- **List sort is always DESC**: `storage::list()` hardcodes `ORDER BY ... DESC` -- no ASC option.
- **FTS5 query sanitization**: `sanitize_fts_query()` in `search.rs` wraps each token in double quotes to force literal matching, preventing FTS5 operator injection (hyphens, colons, asterisks).
- **CLI exit codes**: 0 = success, 1 = not found, 2 = user input error (invalid JSON, bad date, missing args).
- **Python vs CLI dedup defaults**: `PyMemori.insert()` defaults `dedup_threshold=None` (no dedup). The CLI defaults to 0.92 unless `--no-dedup` is passed. Callers of the Python API must pass `dedup_threshold=0.92` explicitly to get CLI-equivalent behavior.
- **CLI `_resolve_id()` inflates access_count**: The helper calls `db.get()` to resolve prefix to full UUID for display, but `get()` bumps access_count as a side effect. `update`, `delete` get +1 spurious bump; `tag` gets +2 (one in `_resolve_id`, one in the final `db.get()` for display).
- **Tag values are always strings**: `memori tag <id> count=42` stores `"42"` (string), not `42` (integer). Metadata filter `{"count": 42}` won't match -- use `{"count": "42"}`.
- **Purge AND/OR mismatch**: When both `--before` and `--type` are specified, the dry-run preview uses AND logic (`db.list()` with both filters), but actual deletion runs `delete_before()` then `delete_by_type()` sequentially (OR logic). Actual deletion will remove more memories than preview shows.
- **Default limit inconsistencies**: CLI search=5, PyO3 search=10, CLI list=20, dashboard list=50, dashboard search=20.
- **GIL release**: Only `search()` releases the Python GIL via `py.allow_threads()`. `insert()` with auto-embedding, `backfill_embeddings()`, and `related()` hold the GIL during CPU-intensive work.
- **Export format**: Always JSONL (one JSON object per line) regardless of `--json`/`--raw` flags.
- **`get_readonly()`**: Reads a memory without bumping access_count or last_accessed. Used by dashboard API to avoid polluting access stats during browsing.
- **Dashboard requires internet**: Chart.js, D3, and chartjs-adapter-date-fns are loaded from CDN (jsdelivr). No local fallback -- charts and graph fail offline, but memory list still works.
- **Timeline scatter cap**: Dashboard timeline chart loads max 500 memories -- larger DBs show only the 500 most recently created.

## Common Change Workflows

### Adding a column to the memories table
1. Add column to `CREATE TABLE` in `schema.rs` + add `ALTER TABLE ADD COLUMN` migration at the next user_version
2. Update `Memory` struct in `types.rs`
3. Update `row_to_memory()` in `storage.rs` (column index changes)
4. Update `memory_to_dict()` in `memori-python/src/lib.rs`

### Adding a new search mode
Add a new arm to the `match` in `search.rs::search()`. Follow existing pattern: take `conn`, query params, `filter`, `limit`, return `Result<Vec<Memory>>`.

### Adding a CLI subcommand
Add a `cmd_<name>()` function and wire it into the argparse subparser in `memori-python/python/memori_cli/__init__.py`. Entry point is `main()` at line ~895.

## Testing Patterns

- **Rust**: 57 integration tests in `memori-core/tests/integration_test.rs` using in-memory SQLite (`:memory:`) via `open_temp()` helper, plus 7 unit tests in `util.rs` (cosine similarity, vec/blob roundtrip)
- **Python**: 37 pytest tests in `memori-python/tests/test_memori.py` using `tmp_path` fixture for DB files
- **Total: 101 tests** (64 Rust + 37 Python) -- no mocking, all real SQLite
- No CLI-level tests exist (only underlying `PyMemori` methods)
- Notable untested paths: `backfill_embeddings()`, `get_readonly()`, `vacuum()`, schema migration upgrades, purge AND/OR behavior, all 18 CLI subcommands at the argparse level

## Documentation Maintenance

When making changes to the codebase, always update `CLAUDE.md` and `README.md` to reflect the current state. This includes new commands, changed architecture, added/removed features, updated CLI flags, and modified workflows. These files are the primary onboarding surface for both humans and AI agents -- stale docs are worse than no docs.

## Key File Paths

| File | Purpose |
|------|---------|
| `memori-core/src/lib.rs` | Memori facade struct, prefix resolution wiring |
| `memori-core/src/search.rs` | All search logic, RRF, decay scoring |
| `memori-core/src/storage.rs` | CRUD, dedup, metadata merge, list |
| `memori-core/src/schema.rs` | DDL, migrations, FTS5 triggers |
| `memori-python/src/lib.rs` | PyO3 bindings (PyMemori class) |
| `memori-python/python/memori_cli/__init__.py` | CLI (argparse, 18 subcommands) |
| `memori-python/python/memori_cli/data/dashboard.html` | Single-file web dashboard (Chart.js + D3) |
| `memori-python/pyproject.toml` | Maturin build config, version, CLI entry point |
| `memori-core/src/embed.rs` | fastembed model init, lazy OnceLock singleton, `embed_text()` / `embed_batch()` |
| `memori-core/src/util.rs` | `cosine_similarity`, `vec_to_blob`/`blob_to_vec` (unsafe pointer casts) |
| `memori-core/tests/integration_test.rs` | 57 integration tests, `open_temp()` helper |
| `memori-core/benches/common/mod.rs` | Benchmark corpus generator, DB seeding helpers |
| `memori-core/benches/search_bench.rs` | Vector/text/hybrid/filtered search benchmarks (1K/10K/100K) |
| `memori-core/benches/crud_bench.rs` | Insert/get/delete/list/count benchmarks (1K/10K/100K) |
| `memori-core/benches/vector_ops_bench.rs` | cosine_similarity, vec/blob conversion, find_duplicate |
| `memori-core/benches/embed_bench.rs` | Embedding model benchmarks (feature-gated) |
| `memori-core/benches/memory_bench.rs` | DB file size + write throughput (1K-1M, standalone) |
| `scripts/bench-table.py` | Parse criterion JSON output into README markdown table |
| `scripts/bench-cli.sh` | CLI-level timing with hyperfine |
| `memori_dev.md` | Developer reference (arch decisions, change workflows) |
| `memori-python/Cargo.toml` | PyO3 crate config (cdylib, pyo3 0.22, abi3-py39) |
| `memori-python/python/memori_cli/data/claude_snippet.md` | Snippet injected by `memori setup` (105 lines, marker-wrapped) |
| `docs/packaging_dev.md` | Open-source packaging strategy and execution plan |
| `LICENSE` | MIT license |
| `.claude/settings.json` | Claude Code project permissions |
