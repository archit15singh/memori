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

**Schema migrations** are tracked via `PRAGMA user_version` (v0 through v3). Each migration is a match arm in `schema.rs::init_db()`.

## Non-Obvious Constraints

- **Vector BLOB format**: f32 arrays as raw bytes, platform-native byte order. `unsafe` pointer casts in `util.rs`
- **FTS5 triggers fire on rowid, not UUID `id`**: the JOIN in `text_search()` bridges this via `m.rowid = fts.rowid`
- **FTS5 delete syntax**: `INSERT INTO memories_fts(memories_fts, rowid, content) VALUES('delete', ...)` -- FTS5's documented removal mechanism
- **Metadata filter is flat equality only**: `build_filter_clause()` in `search.rs` converts JSON to `json_extract()` WHERE clauses -- no nested paths, no operators
- **Prefix ID resolution**: `LIKE prefix%` on UUID primary key maps to a B-tree range scan. The facade in `lib.rs` wraps get/get_readonly/update/delete/touch/set_access_stats/related with prefix resolution
- **Decay scoring**: logarithmic access boost + exponential time decay (~69 day half-life). `access_count == 0` guard prevents penalizing newly-stored memories
- **Dedup threshold**: cosine similarity >= 0.92 between same-type memories triggers update instead of insert

## Common Change Workflows

### Adding a column to the memories table
1. Add column to `CREATE TABLE` in `schema.rs` + add `ALTER TABLE ADD COLUMN` migration at the next user_version
2. Update `Memory` struct in `types.rs`
3. Update `row_to_memory()` in `storage.rs` (column index changes)
4. Update `memory_to_dict()` in `memori-python/src/lib.rs`

### Adding a new search mode
Add a new arm to the `match` in `search.rs::search()`. Follow existing pattern: take `conn`, query params, `filter`, `limit`, return `Result<Vec<Memory>>`.

### Adding a CLI subcommand
Add a `cmd_<name>()` function and wire it into the argparse subparser in `memori-python/python/memori_cli/__init__.py`. Entry point is `main()` at line ~870.

## Testing Patterns

- **Rust**: 57 integration tests in `memori-core/tests/integration_test.rs` using in-memory SQLite (`:memory:`) via `open_temp()` helper
- **Python**: 37 pytest tests in `memori-python/tests/test_memori.py` using `tmp_path` fixture for DB files
- Both suites test the same behaviors at their respective layers -- no mocking, all real SQLite
- No CLI-level tests exist (only underlying `PyMemori` methods)

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
| `memori_dev.md` | Developer reference (arch decisions, change workflows) |
