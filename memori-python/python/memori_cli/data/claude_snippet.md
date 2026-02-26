<!-- memori:start -->
## Memori -- Persistent Agent Memory

Persistent memory across sessions via `memori` CLI. DB at `~/.claude/memori.db`.
Search matches both content text and metadata values. Embeddings are auto-generated on store -- no manual `--vector` needed.

### Session Start (always do this)

1. Run `memori context "<task topic>"` to load relevant memories and recent activity.
2. If relevant matches exist, briefly tell the user what you already know about their topic from past sessions.
3. If results include memories that conflict with what you now see in the codebase, update them: `memori update <id> --content "corrected ..."` or `memori tag <id> status=outdated`.
4. If the database is empty (total: 0), skip to working -- memories will accumulate naturally from the triggers below.
5. If `memori stats` shows low embedding coverage (e.g. <80%), run `memori embed` to backfill embeddings on old memories for better search quality.

### When to Store

Embeddings are auto-generated at store time -- just provide the text content and optional metadata. Deduplication is also automatic: storing similar content of the same type updates the existing memory instead of creating a duplicate.

**After fixing a bug where the root cause was not obvious from the error message** -- store the root cause chain, not the fix itself (the fix is in git): `memori store "<symptom -> root cause -> why>" --meta '{"type": "debugging", "topic": "<area>"}'`

**After choosing between alternatives** -- store what was chosen and what was rejected with reasoning: `memori store "<chose X over Y because Z>" --meta '{"type": "decision", "topic": "<area>"}'`

**When user explicitly states a preference** about tools, style, or workflow: `memori store "<preference>" --meta '{"type": "preference"}'`

**After mapping unfamiliar code** -- store the structural insight that would save the next session 10+ minutes of reading: `memori store "<how subsystem X works>" --meta '{"type": "architecture", "topic": "<subsystem>"}'`

**When a reusable pattern emerges** across 2+ instances: `memori store "<pattern: when X, do Y because Z>" --meta '{"type": "pattern", "topic": "<domain>"}'`

**When leaving unfinished work** -- store what remains and any context a fresh session would need: `memori store "<remaining tasks + blockers + key context>" --meta '{"type": "roadmap", "topic": "<project>"}'`

### When NOT to Store

- Facts already in CLAUDE.md, README, or inline code comments (don't duplicate)
- Session-specific context (current file paths, variable names, temp state)
- Trivially re-discoverable information (file locations, function signatures)
- Anything you're uncertain about -- verify first, store after
- Don't worry about storing duplicates -- memori auto-merges similar memories of the same type

### When to Search

**Before investigating a bug** -- check if a past session already debugged this area: `memori search --text "<error or area>"` or `memori search --filter '{"type": "debugging"}'`

**Before designing anything** -- check for existing architecture notes and past decisions: `memori search --text "<component>"` or `memori search --filter '{"type": "architecture"}'`

**Before deep-diving into unfamiliar code** -- a past session may have already mapped it: `memori search --text "<subsystem or concept>"`

### Self-Maintenance

**When you discover a stored memory is wrong** -- update or delete it immediately. Stale memories are worse than no memories.

**When `memori stats` shows 50+ memories** -- review type distribution. If any type dominates (>60%), the storage triggers may be too aggressive for that type. Consider if those memories are genuinely useful.

**When scratch/temporary memories accumulate** -- clean up: `memori purge --type temporary` (previews first), then `--confirm` to delete.

### Content Quality

Each memory should be **1-3 sentences**: the insight, the context, and optionally the evidence. If you need more, you're storing a document, not a memory -- use a file instead.

Good: "FTS5 query sanitization: user search terms with hyphens crash MATCH because FTS5 interprets - as NOT operator. Fix: wrap each token in double quotes before passing to MATCH."

Bad: "Fixed a bug." (no context for future retrieval)
Bad: (3 paragraphs reproducing an entire investigation) -- store the conclusion, not the journey.

### Memory Types

| Type | Store when... |
|------|--------------|
| `debugging` | Root cause was non-obvious, worth remembering |
| `decision` | Chose between alternatives with trade-offs |
| `architecture` | Mapped how a subsystem works |
| `pattern` | Same approach worked across 2+ situations |
| `preference` | User stated a tool/style/workflow preference |
| `fact` | Learned a stable, non-obvious fact about the codebase or environment |
| `roadmap` | Leaving unfinished work for a future session |
| `temporary` | Scratch notes expected to be purged later |

### Commands Reference

| Command | Purpose |
|---------|---------|
| `memori context "<topic>"` | Load relevant + recent memories + type stats |
| `memori store "<text>" --meta '{"type": "..."}'` | Store with typed metadata (auto-embeds, auto-dedup) |
| `memori search --text "<query>"` | Full-text + vector hybrid search |
| `memori search --filter '{"type": "..."}'` | Filter by metadata fields |
| `memori update <id> --content/--meta` | Correct or enrich existing memory |
| `memori tag <id> key=value ...` | Merge key-value tags into metadata |
| `memori get <id>` | Read full memory by ID |
| `memori delete <id>` | Remove single memory |
| `memori embed` | Backfill embeddings on old memories |
| `memori purge --type/--before` | Bulk preview (add `--confirm` to delete) |
| `memori export > backup.jsonl` | JSONL backup to stdout |
| `memori import < backup.jsonl` | Restore from JSONL stdin |
| `memori stats` | DB size, memory count, type distribution, embedding coverage |
<!-- memori:end -->
