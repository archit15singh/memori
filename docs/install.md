# Installing Memori for Claude Code

## Quick Start

```bash
git clone https://github.com/archit-15dev/memori.git
cd memori
```

Then open Claude Code in this directory and ask it to install memori. It will read this file and follow the steps below.

---

## Prerequisites

- **Rust toolchain** (`rustc` + `cargo`) -- [rustup.rs](https://rustup.rs/)
- **Python 3.9+**
- **uv** (recommended) -- `curl -LsSf https://astral.sh/uv/install.sh | sh`

Verify:

```bash
cargo --version   # any recent stable
python3 --version # 3.9+
uv --version      # 0.4+
```

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

Run from your home directory (not the project directory) so the snippet targets your global `~/.claude/CLAUDE.md`:

```bash
cd ~ && memori setup
```

This injects a behavioral snippet that teaches Claude Code when and how to use memori -- what to store, when to search, how to self-maintain.

**Verify:**

```bash
memori setup --show              # preview the snippet
grep "memori:start" ~/.claude/CLAUDE.md  # confirm injection
```

## Step 3: Verify Claude Code Can Use It

Store a test memory. The first `store` command downloads the embedding model (~90MB, cached at `~/.fastembed_cache/`). Subsequent calls are fast.

```bash
memori store "Memori installed and configured for Claude Code" --meta '{"type": "fact"}'
```

**Verify the full chain:**

```bash
memori count     # Expected: 1
memori stats     # Expected: 1 memory, 100% embedded
```

## Step 4: Test It Out

Run through the core workflow to confirm everything works end-to-end. Use a temp DB to avoid polluting your real memory store:

```bash
# Store a few test memories
memori --db /tmp/memori_verify.db store "FTS5 hyphens crash MATCH because - is the NOT operator" --meta '{"type": "debugging", "topic": "sqlite"}'
memori --db /tmp/memori_verify.db store "Chose SQLite over Postgres for zero-config portability" --meta '{"type": "decision", "topic": "database"}'
memori --db /tmp/memori_verify.db store "User prefers uv over pip for Python tooling" --meta '{"type": "preference"}'

# Search (should return ranked results)
memori --db /tmp/memori_verify.db search --text "SQLite"

# Context retrieval (simulates session start)
memori --db /tmp/memori_verify.db context "database choices"

# Dedup test (should say "deduplicated" since content matches first store)
memori --db /tmp/memori_verify.db store "FTS5 hyphens crash MATCH because - is the NOT operator" --meta '{"type": "debugging"}'

# Export/import round-trip
memori --db /tmp/memori_verify.db export > /tmp/memori_verify.jsonl
memori --db /tmp/memori_verify2.db import < /tmp/memori_verify.jsonl
memori --db /tmp/memori_verify2.db count
# Should match: 3

# Cleanup
rm /tmp/memori_verify.db /tmp/memori_verify2.db /tmp/memori_verify.jsonl 2>/dev/null
```

**Expected results:**
- `search` returns ranked results with the SQLite-related memories at top
- `context` shows relevant memories grouped by section
- Second store of identical debugging content reports "deduplicated"
- Import count matches export count (3)

## Step 5: Verify and Fix

If something didn't work:

| Symptom | Fix |
|---------|-----|
| `memori: command not found` | Add uv's bin dir to PATH: `export PATH="$HOME/.local/bin:$PATH"` and restart shell |
| Build fails with "cargo not found" | Install Rust: `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs \| sh` |
| Build fails with Python errors | Ensure Python 3.9+: `python3 --version`. On macOS: `brew install python@3.12` |
| `memori setup` writes to project CLAUDE.md | Run from `~`, not from inside a project: `cd ~ && memori setup` |
| Snippet missing from `~/.claude/CLAUDE.md` | File may not exist yet. Create it: `touch ~/.claude/CLAUDE.md && memori setup` |
| First `store` hangs or is slow | Normal -- downloading the embedding model (~90MB). Wait ~1 min. Cached after first run. |
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
