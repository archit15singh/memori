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

## Demo

### Store memories with auto-embeddings and dedup

```bash
$ memori store "FTS5 hyphens crash MATCH because - is the NOT operator. Fix: quote each token." \
    --meta '{"type": "debugging", "topic": "sqlite"}'
Stored: b338b67f-b40b-4243-9219-2a2375e3d249

$ memori --json store "Chose SQLite over Postgres for zero-config portability." \
    --meta '{"type": "decision", "topic": "architecture"}'
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
$ memori --json search --text "sqlite" --limit 1
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

Compact single-line JSON for piping (saves tokens for AI agents):

```bash
$ memori --raw search --text "sqlite" --limit 1
[{"id": "6bf65b6f-...", "content": "Chose SQLite over Postgres...", "score": 0.0328, ...}]
```

Force FTS5-only when speed matters (skips embedding model):

```bash
$ memori search --text "sqlite" --text-only
```

### Context loading (one call for session start)

Loads relevant matches + recent memories + type stats:

```bash
$ memori context "sqlite architecture" --limit 3
## Relevant Memories: "sqlite architecture"

- 6bf65b6f [3.2232] Chose SQLite over Postgres for zero-config portability.

## Recent Memories

- 6bf65b6f [decision] Chose SQLite over Postgres...
- b338b67f [debugging] FTS5 hyphens crash MATCH...

## Stats

Total: 12 memories
Types: debugging: 4, decision: 4, architecture: 2, fact: 1, preference: 1
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

```bash
# Store
memori store "memory text" --meta '{"type": "debugging"}'
memori store "text" --no-embed          # skip auto-embedding
memori store "text" --no-dedup          # skip dedup check

# Search
memori search --text "query"            # hybrid search (FTS5 + vector)
memori search --text "query" --text-only  # FTS5-only (faster)
memori search --filter '{"type": "debugging"}'
memori search --limit 20

# Context (relevant + recent + stats)
memori context "topic"

# Get / Update / Tag / Delete
memori get <id>                         # vectors stripped by default
memori get <id> --include-vectors       # include vector data
memori update <id> --content "new text"
memori tag <id> verified=true topic=fts5
memori delete <id>

# Export / Import (JSONL)
memori export > backup.jsonl
memori import < backup.jsonl
memori import --new-ids < backup.jsonl

# Maintenance
memori stats                            # DB size, types, embedding coverage
memori count                            # quick count
memori embed                            # backfill embeddings for old memories
memori gc                               # compact database (SQLite VACUUM)
memori purge --type temporary           # preview what would be deleted
memori purge --type temporary --confirm # actually delete
memori purge --before 2025-01-01 --confirm

# Output modes (work with all commands)
memori --json search --text "query"     # pretty JSON
memori --raw search --text "query"      # compact single-line JSON (implies --json)
```

## Python API

```python
from memori import PyMemori

db = PyMemori("memories.db")

# Store (auto-embeds, auto-dedup)
result = db.insert("user prefers dark mode", metadata={"type": "preference"})
# result = {"id": "abc-123", "action": "created"}

# Search
results = db.search(text="dark mode")         # hybrid search
results = db.search(text="dark mode", text_only=True)  # FTS5-only
results = db.search(vector=[1.0, 0.0, ...], limit=5)
results = db.search(filter={"type": "preference"})

# Update, tag, delete
db.update(result["id"], content="updated text", metadata={"type": "fact"})
db.delete(result["id"])

# Bulk operations
dist = db.type_distribution()        # {"preference": 3, "fact": 1}
db.delete_before(timestamp)          # bulk delete by age
db.delete_by_type("temporary")       # bulk delete by type
db.insert_with_id("custom-id", ...)  # import with preserved IDs
db.set_access_stats("id", last_accessed=ts, access_count=5)  # restore access stats
db.vacuum()                          # compact database

# Embeddings
db.backfill_embeddings(batch_size=50)
stats = db.embedding_stats()         # {"embedded": 10, "total": 12}
vec = db.embed("some text")          # get raw embedding vector
```

## Architecture

- **memori-core** (Rust): SQLite + FTS5 full-text search + cosine similarity vector search. FTS5 indexes both content and metadata so `search --text "kafka"` finds memories where "kafka" appears in either. Auto-embeddings via AllMiniLM-L6-V2 (fastembed). Schema migrations via `PRAGMA user_version`.
- **memori-python** (PyO3 + maturin): Rust bindings exposed as `PyMemori` class. Mutex-wrapped for thread safety.
- **memori-cli** (Python): Thin CLI layer with `--json` and `--raw` output on every command for agent consumption. Vectors stripped from output by default (10KB per memory -> ~500 bytes).

## License

MIT
