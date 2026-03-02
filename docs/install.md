# Installing Memori for Claude Code

## Quick Start

```bash
git clone https://github.com/archit-15dev/memori.git
cd memori
```

Then open Claude Code in this directory and ask it to install memori. It will read this file and follow the steps below.

---

## Prerequisites

Check each prerequisite individually:

### Rust toolchain

```bash
cargo --version
```

Expected: any string starting with `cargo`

**Fix** if not found: `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh` then restart shell. If Rust is installed but `cargo` is not in PATH, try `source ~/.cargo/env && cargo --version`.

### Python 3.9+

```bash
python3 --version
```

Expected: `Python 3.9` or higher

**Fix** if too old or not found: On macOS, `brew install python@3.12`. On Linux, `apt-get install python3.12` (or similar). Restart shell after installing.

### uv (0.4+)

```bash
uv --version
```

Expected: `uv` followed by version `0.4` or higher

**Fix** if not found: `curl -LsSf https://astral.sh/uv/install.sh | sh` then restart shell.

## Step 1: Install the CLI

From the repository root:

```bash
cd memori-python && uv tool install --from . memori
```

This compiles the Rust core (SQLite + fastembed bundled), builds PyO3 bindings, and places the `memori` binary on PATH. First build takes 2-3 minutes.

**Verify:**

```bash
memori --version
# Expected: memori 0.6.0
```

If `memori` is not found, ensure uv's tool bin directory is on your PATH:

```bash
# Add to ~/.zshrc or ~/.bashrc:
export PATH="$HOME/.local/bin:$PATH"
```

## Step 2: Configure for Claude Code

> **CRITICAL WARNING**: Run from your home directory (`~`), NOT from the project directory.
>
> `memori setup` writes the snippet to `~/.claude/tools/memori/SNIPPET.md` and adds a reference pointer to your CLAUDE.md. If you run from inside the project, the pointer is added to the project's local CLAUDE.md instead of your global `~/.claude/CLAUDE.md`.

```bash
cd ~ && memori setup
```

This writes a behavioral snippet to `~/.claude/tools/memori/SNIPPET.md` that teaches Claude Code when and how to use memori -- what to store, when to search, how to self-maintain.

Expected output (one of):
- `Configured memori. Snippet at /Users/<your-username>/.claude/tools/memori/SNIPPET.md, reference in /Users/<your-username>/.claude/CLAUDE.md`
- `Updated memori snippet at /Users/<your-username>/.claude/tools/memori/SNIPPET.md (v...)`
- `Memori already configured at /Users/<your-username>/.claude/tools/memori/SNIPPET.md`

**Verify setup:**

```bash
test -f ~/.claude/tools/memori/SNIPPET.md && echo "✓ Snippet found" || echo "✗ Not found"
grep -c "memori:reference" ~/.claude/CLAUDE.md
# Expected: 1
```

If the pointer is in the wrong CLAUDE.md (project-local instead of global):

```bash
cd ~ && memori setup --undo   # undo the wrong setup
cd ~ && memori setup          # re-setup from home directory
```

## Step 3: Verify Claude Code Can Use It

Store a test memory. **The first `store` command downloads the embedding model (~90MB) to `~/.fastembed_cache/`**. This takes **1–2 minutes** the first time. Subsequent calls use the cached model and are instant.

```bash
memori store "Memori installed and configured for Claude Code" --meta '{"type": "fact"}'
```

Expected: output contains `stored` or `deduplicated`

**Verify the full chain:**

```bash
memori stats
# Expected: 1 memory, 100% embedding coverage
```

**STOP if embedding coverage is 0%**: Run `memori embed` to backfill embeddings.

## Step 4: Test It Out

Run through the core workflow to confirm everything works end-to-end. Use a temp DB to avoid polluting your real memory store:

```bash
DB=/tmp/memori_verify.db

# Store a few test memories
memori --db $DB store "FTS5 hyphens crash MATCH because - is the NOT operator" --meta '{"type": "debugging", "topic": "sqlite"}'
memori --db $DB store "Chose SQLite over Postgres for zero-config portability" --meta '{"type": "decision", "topic": "database"}'
memori --db $DB store "User prefers uv over pip for Python tooling" --meta '{"type": "preference"}'

# Verify count
memori --db $DB count
# Expected: 3

# Search (should return ranked results, SQLite memories at top)
memori --db $DB search --text "SQLite"
# Expected: SQLite-related memories ranked at top

# Context retrieval (simulates session start)
memori --db $DB context "database choices"
# Expected: memories grouped by section, relevant ones ranked higher

# Dedup test (identical content + same type = update, not insert)
memori --db $DB store "FTS5 hyphens crash MATCH because - is the NOT operator" --meta '{"type": "debugging"}'
# Expected: output contains "deduplicated"

# Export/import round-trip
memori --db $DB export > /tmp/memori_verify.jsonl
memori --db /tmp/memori_verify2.db import < /tmp/memori_verify.jsonl
memori --db /tmp/memori_verify2.db count
# Expected: 3 (should match original DB count)

# Cleanup
rm /tmp/memori_verify.db /tmp/memori_verify2.db /tmp/memori_verify.jsonl 2>/dev/null
```

**Expected results:**
- `count` returns `3`
- `search` returns ranked results with SQLite-related memories at top
- `context` shows relevant memories grouped by section
- Dedup detects identical debugging memory and reports "deduplicated"
- Import count matches export count (3)

## Step 5: Explore the Dashboard

Memori includes a web dashboard to visualize and browse your memories. Open it now:

```bash
memori ui
```

Expected:
- Browser auto-opens to http://127.0.0.1:8899
- Dashboard loads with your stored memories and charts

**Dashboard Features:**

The left sidebar shows:
- **Total Memories**: Live count of all memories in your database
- **Embedding Coverage**: Percentage of memories with embeddings (click to run `memori embed` if needed)
- **Types**: Donut chart showing distribution of memory types (click segments to filter the list)
- **Timeline**: Scatter plot with creation date on X-axis and access count on Y-axis (shows memory age vs usage patterns)

The main area displays:
- **Memory Cards**: 20 memories per page, each showing ID, type badge, content preview, relative timestamp, access count
- **Live Search**: Text input at top filters by content using hybrid FTS5 + vector search
- **Type Filter**: Dropdown to show only memories of a specific type
- **Sort Options**: Create, Updated, Accessed, or Access Count (click column headers)
- **Date Range Pickers**: Filter memories within a date range

**Expand a Memory:**
- Click any card to see full content, all metadata, and related memories
- "Explore Connections" button shows a D3 force-directed graph of related memories
- Graph nodes are sized by access count and colored by type

**Try It Out:**

Populate the dashboard with test memories (using your real database):

```bash
memori store "Memori dashboard shows memory stats, search, timeline, and memory relationships" --meta '{"type": "fact"}'
memori store "Debugging pattern: grep logs → narrow time window → find root cause → verify fix" --meta '{"type": "pattern", "topic": "debugging"}'
memori store "Chose Rust for memori core for zero-GC performance and seamless PyO3 Python bindings" --meta '{"type": "decision", "topic": "architecture"}'

# Dashboard updates in real-time -- refresh browser to see new memories
```

Then refresh the browser to see:
- Updated "Total Memories" count
- New colors in the Types donut chart
- New dots on the Timeline
- Memories searchable and filterable by type

**Close the Dashboard:**

Press `Ctrl+C` in the terminal running `memori ui`. (The database remains intact.)

## Step 6: Verify and Fix

If something didn't work:

| Symptom | Fix |
|---------|-----|
| `memori: command not found` | Add uv's bin dir to PATH: `export PATH="$HOME/.local/bin:$PATH"` and restart shell |
| Build fails with "cargo not found" | Install Rust: `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs \| sh` |
| Build fails with Python errors | Ensure Python 3.9+: `python3 --version`. On macOS: `brew install python@3.12` |
| `memori setup` writes pointer to project CLAUDE.md | Undo: `cd ~ && memori setup --undo`. Then: `cd ~ && memori setup` from home directory |
| Snippet file missing at `~/.claude/tools/memori/SNIPPET.md` | Re-run setup: `cd ~ && memori setup` |
| Reference missing from `~/.claude/CLAUDE.md` | File may not exist yet. Create it: `mkdir -p ~/.claude && touch ~/.claude/CLAUDE.md && cd ~ && memori setup` |
| Multiple references in CLAUDE.md | Rare. Open file and keep only one `<!-- memori:reference...memori:reference:end -->` block |
| First `store` hangs or is slow | Normal -- downloading the embedding model (~90MB). Wait 1–2 min. Cached after first run. |
| Search returns no results | Check `memori stats` -- if embedding coverage is <100%, run `memori embed` to backfill |
| Dedup didn't trigger | Content must be nearly identical AND same `type` in metadata. Check both match. |
| `memori ui` says "Address already in use" | Port 8899 is taken. Use: `memori ui --port 9000` |
| Dashboard charts show "Charts require internet connection" | This is expected (Chart.js and D3 are loaded from CDN). Charts display when online; memory list always works |
| Browser doesn't auto-open for `memori ui` | Use `memori ui --no-open` and manually visit http://127.0.0.1:8899. Or configure your default browser. |

If tests pass but Claude Code doesn't seem to use memori, verify the reference is in the **global** file:

```bash
cat ~/.claude/CLAUDE.md | grep -c "memori:reference"
# Expected: 1
```

Also verify the snippet file exists:

```bash
test -f ~/.claude/tools/memori/SNIPPET.md && echo "✓ Snippet found"
```

Then start a new Claude Code session -- the snippet is read at session start.

---

## Upgrading

After pulling new code:

```bash
cd memori/memori-python && uv tool install --from . memori --force
cd ~ && memori setup  # re-run from ~ to update the snippet if version changed
```

## Uninstalling

```bash
cd ~ && memori setup --undo  # remove reference from CLAUDE.md and snippet file (must run before uninstalling)
uv tool uninstall memori     # remove the CLI binary
```

The database at `~/.claude/memori.db` and model cache at `~/.fastembed_cache/` are left behind. Delete manually if desired.
