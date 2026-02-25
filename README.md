# Memori

Persistent memory for AI coding agents. SQLite + FTS5 + vector search in a single binary.

Memori gives Claude Code (and other AI agents) the ability to remember decisions, debugging lessons, architecture notes, and user preferences across sessions -- so every session starts smarter than the last.

## Install

Requires Rust toolchain and Python 3.9+.

```bash
# Clone and install
git clone https://github.com/archit-singhh/memori.git
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

## CLI Reference

```bash
# Store
memori store "FTS5 hyphens crash MATCH" --meta '{"type": "debugging", "topic": "sqlite"}'

# Search (matches both content and metadata)
memori search --text "sqlite"
memori search --filter '{"type": "debugging"}'

# Context loading (relevant + recent + stats in one call)
memori context "sqlite"

# Get / Update / Tag / Delete
memori get <id>
memori update <id> --content "corrected text"
memori tag <id> verified=true topic=fts5
memori delete <id>

# Export / Import (JSONL)
memori export > backup.jsonl
memori import < backup.jsonl
memori import --new-ids < backup.jsonl   # fresh UUIDs

# Bulk cleanup (dry-run by default)
memori purge --type temporary             # preview
memori purge --type temporary --confirm   # delete
memori purge --before 2025-01-01 --confirm

# Stats
memori stats
memori count

# All commands support --json for machine-readable output
memori --json search --text "kafka"
```

## Python API

```python
from memori import PyMemori

db = PyMemori("memories.db")

# Store and search
mid = db.insert("user prefers dark mode", metadata={"type": "preference"})
results = db.search(text="dark mode")
results = db.search(vector=[1.0, 0.0, 0.0], limit=5)
results = db.search(filter={"type": "preference"})

# Update, tag, delete
db.update(mid, content="updated text", metadata={"type": "fact"})
db.delete(mid)

# Bulk operations
dist = db.type_distribution()        # {"preference": 3, "fact": 1}
db.delete_before(timestamp)          # bulk delete by age
db.delete_by_type("temporary")       # bulk delete by type
db.insert_with_id("custom-id", ...)  # import with preserved IDs
```

## Architecture

- **memori-core** (Rust): SQLite + FTS5 full-text search + cosine similarity vector search. FTS5 indexes both content and metadata so `search --text "kafka"` finds memories where "kafka" appears in either. Schema migrations via `PRAGMA user_version`.
- **memori-python** (PyO3 + maturin): Rust bindings exposed as `PyMemori` class. Mutex-wrapped for thread safety.
- **memori-cli** (Python): Thin CLI layer with `--json` output on every command for agent consumption.

## License

MIT
