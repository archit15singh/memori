---
name: install
description: >
  Install memori from source and configure it for Claude Code. Use when the user
  says "install", "install memori", "set this up", "set up memori", or any
  equivalent request to get memori working on the current machine.
---

# Install Memori — Automated Setup Skill

**Error Policy**: Stop immediately on any failed verification. Report: (1) command run, (2) actual output, (3) expected output, (4) how to fix. Do not proceed to the next phase.

---

## Phase 1: Verify Prerequisites

Check each prerequisite individually. STOP immediately if any check fails.

### Rust toolchain

```bash
cargo --version
```

Expected output: any string starting with `cargo`

**If fails**: Install Rust via `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh`, then restart your shell and verify again. If Rust is installed but `cargo` is not in PATH, run `source ~/.cargo/env && cargo --version`.

---

### Python 3.9+

```bash
python3 --version
```

Expected output: `Python 3.9` or higher (e.g., `Python 3.12.1`)

**If fails (too old or not found)**:
- macOS: `brew install python@3.12`
- Linux: `apt-get install python3.12` (or similar for your distro)
- Windows: [python.org](https://www.python.org/downloads/)

Restart shell and verify again.

---

### uv (0.4+)

```bash
uv --version
```

Expected output: `uv` followed by version `0.4` or higher

**If fails**: Install via `curl -LsSf https://astral.sh/uv/install.sh | sh`, restart your shell, and verify again.

---

## Phase 2: Build and Install CLI

From the project root (the directory containing this CLAUDE.md file):

```bash
cd memori-python && uv tool install --from . memori
```

**Note**: First build compiles the Rust core — takes 2–5 minutes. Rust compiler output is normal.

**Expected**: Final output line contains `Installed 1 executable: memori`

### Verify CLI installation

```bash
memori --version
```

Expected: `memori 0.6.0`

**If command not found**:

1. Check if the binary exists: `ls ~/.local/bin/memori`
   - If it exists, your PATH is missing uv's bin directory. Add this to `~/.zshrc` or `~/.bashrc`:
     ```bash
     export PATH="$HOME/.local/bin:$PATH"
     ```
     Then run `source ~/.zshrc` (or `~/.bashrc`), restart your shell, and try `memori --version` again.

2. If the binary doesn't exist, the build failed silently. Re-run the Phase 2 commands above and look for error messages in the output.

---

## Phase 3: Configure Claude Code Snippet

⚠️ **CRITICAL**: Run from your home directory (`~`), NOT from inside the project directory. The `memori setup` command searches for CLAUDE.md starting from the current working directory. Running from inside a project injects the snippet into the project's local CLAUDE.md instead of your global `~/.claude/CLAUDE.md`.

```bash
cd ~ && memori setup
```

Expected output (one of the following):
- `Added memori snippet to /Users/<your-username>/.claude/CLAUDE.md`
- `Updated memori snippet in /Users/<your-username>/.claude/CLAUDE.md (...)`
- `Memori snippet already present in /Users/<your-username>/.claude/CLAUDE.md`

**STOP if the output path is inside the project directory** (e.g., contains `memori/CLAUDE.md`):

```bash
cd ~ && memori setup --undo      # undo the wrong injection
cd ~ && memori setup             # re-inject into global file
```

---

## Phase 4: Verify Global CLAUDE.md Was Updated

```bash
grep -c "memori:start" ~/.claude/CLAUDE.md
```

Expected: `1`

**If result is 0**:
- File doesn't exist: Run `mkdir -p ~/.claude && touch ~/.claude/CLAUDE.md && cd ~ && memori setup`
- File exists but no snippet: Setup ran from the wrong directory or failed; re-run Phase 3

**If result is 2 or more** (duplicate injections):
- Open `~/.claude/CLAUDE.md` in your editor
- Find and delete all but one `<!-- memori:start ... memori:end ... -->` block
- Save the file

---

## Phase 5: Download Embedding Model

The first `store` command downloads the embedding model (~90MB to `~/.fastembed_cache/`). This takes 1–2 minutes the first time. Subsequent calls use the cached model and are instant.

```bash
memori store "Memori installed and configured for Claude Code" --meta '{"type": "fact"}'
```

Expected output: contains `stored` or `deduplicated` (if re-installing)

**Verify embedding coverage**:

```bash
memori stats
```

Expected: `Embedding coverage: 100%` (or close to it)

**If coverage is 0%**: Run `memori embed` to backfill.

---

## Phase 6: E2E Verification

Use a temporary database to verify the full workflow without touching your real memory store:

```bash
DB=/tmp/memori_verify.db

# Store 3 test memories with different types
memori --db $DB store "FTS5 hyphens crash MATCH because - is the NOT operator" --meta '{"type": "debugging", "topic": "sqlite"}'
memori --db $DB store "Chose SQLite over Postgres for zero-config portability" --meta '{"type": "decision", "topic": "database"}'
memori --db $DB store "User prefers uv over pip for Python tooling" --meta '{"type": "preference"}'

# Verify count
memori --db $DB count
# Expected: 3

# Verify search returns ranked results (SQLite memories should rank highest)
memori --db $DB search --text "SQLite"
# Expected: SQLite-related memories at the top

# Verify context retrieval (session start simulation)
memori --db $DB context "database choices"
# Expected: memories grouped by section, relevant ones ranked higher

# Verify dedup (identical content + same type = update, not insert)
memori --db $DB store "FTS5 hyphens crash MATCH because - is the NOT operator" --meta '{"type": "debugging"}'
# Expected output: contains "deduplicated"

# Verify export/import round-trip
memori --db $DB export > /tmp/memori_verify.jsonl
memori --db /tmp/memori_verify2.db import < /tmp/memori_verify.jsonl
memori --db /tmp/memori_verify2.db count
# Expected: 3 (same as original DB)

# Cleanup
rm /tmp/memori_verify.db /tmp/memori_verify2.db /tmp/memori_verify.jsonl 2>/dev/null
```

**Expected behaviors**:
- `search` returns results ranked by relevance
- `context` groups memories by type/topic
- Dedup detects identical debugging memory and reports "deduplicated"
- Import count matches export count (3)

---

## Phase 7: Installation Complete

All phases passed! ✓

**Next steps:**
1. Start a new Claude Code session (quit and reopen, or just run `claude` in a new terminal)
2. The snippet in `~/.claude/CLAUDE.md` is loaded at session start
3. To confirm, run: `memori context "test"` in your next session — it should surface any relevant memories

**Troubleshooting**: If you encounter issues after reinstalling, see the troubleshooting table in `docs/install.md`.
