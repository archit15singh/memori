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
> `memori setup` searches for CLAUDE.md starting from the current working directory. If you run from inside the project, it injects into the project's local CLAUDE.md instead of your global `~/.claude/CLAUDE.md`.

```bash
cd ~ && memori setup
```

This injects a behavioral snippet that teaches Claude Code when and how to use memori -- what to store, when to search, how to self-maintain.

Expected output (one of):
- `Added memori snippet to /Users/<your-username>/.claude/CLAUDE.md`
- `Updated memori snippet in /Users/<your-username>/.claude/CLAUDE.md (...)`
- `Memori snippet already present in /Users/<your-username>/.claude/CLAUDE.md`

**STOP if the output path is inside the project directory** (e.g., contains `memori/CLAUDE.md`):

```bash
cd ~ && memori setup --undo   # undo the wrong injection
cd ~ && memori setup          # re-inject into global file
```

**Verify injection:**

```bash
grep -c "memori:start" ~/.claude/CLAUDE.md
# Expected: 1
```

If `0`, the file may not exist yet: `mkdir -p ~/.claude && touch ~/.claude/CLAUDE.md && cd ~ && memori setup`

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

## Step 5: Verify and Fix

If something didn't work:

| Symptom | Fix |
|---------|-----|
| `memori: command not found` | Add uv's bin dir to PATH: `export PATH="$HOME/.local/bin:$PATH"` and restart shell |
| Build fails with "cargo not found" | Install Rust: `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs \| sh` |
| Build fails with Python errors | Ensure Python 3.9+: `python3 --version`. On macOS: `brew install python@3.12` |
| `memori setup` writes to project CLAUDE.md | Undo: `cd ~ && memori setup --undo`. Then: `cd ~ && memori setup` from home directory |
| Snippet missing from `~/.claude/CLAUDE.md` | File may not exist yet. Create it: `mkdir -p ~/.claude && touch ~/.claude/CLAUDE.md && cd ~ && memori setup` |
| Snippet is 2+ (duplicate injections) | Open `~/.claude/CLAUDE.md`, delete extra `<!-- memori:start...memori:end -->` blocks, keep exactly one |
| First `store` hangs or is slow | Normal -- downloading the embedding model (~90MB). Wait 1–2 min. Cached after first run. |
| Search returns no results | Check `memori stats` -- if embedding coverage is <100%, run `memori embed` to backfill |
| Dedup didn't trigger | Content must be nearly identical AND same `type` in metadata. Check both match. |

If tests pass but Claude Code doesn't seem to use memori, verify the snippet is in the **global** file:

```bash
cat ~/.claude/CLAUDE.md | grep -c "memori:start"
# Expected: 1
```

Then start a new Claude Code session -- the snippet is read at session start.

---

## Upgrading

After pulling new code:

```bash
cd memori/memori-python && uv tool install --from . memori --force
memori setup  # re-run from ~ to update the snippet if version changed
```

## Uninstalling

```bash
uv tool uninstall memori   # remove the CLI binary
cd ~ && memori setup --undo  # remove snippet from CLAUDE.md (run before uninstalling, or manually delete the memori:start/end block)
```

The database at `~/.claude/memori.db` and model cache at `~/.fastembed_cache/` are left behind. Delete manually if desired.
