<!-- memori:start v0.6.0 -->
## Memori -- Persistent Agent Memory

Persistent memory across sessions via `memori` CLI. DB at `~/.claude/memori.db`.
Hybrid search (FTS5 + cosine vectors) auto-vectorizes text queries. IDs can be shortened to unique prefixes. Use `--raw` for compact single-line JSON.

### Session Start (always do this)

1. Run `memori context "<task topic>"` (or `--compact` for minimal JSON) to load relevant memories.
2. If matches exist, tell the user what you already know. If memories conflict with current codebase, update them.
3. If empty (total: 0), skip -- memories accumulate from triggers below.
4. If `memori stats` shows <80% embedding coverage, run `memori embed`.

### When to Store

Auto-embeds and auto-deduplicates. Just provide content + type metadata. Each memory: 1-3 sentences (insight + context). Store conclusions, not journeys.

- **Non-obvious bug root cause**: `memori store "<symptom -> root cause -> why>" --meta '{"type": "debugging", "topic": "<area>"}'`
- **Decision with trade-offs**: `memori store "<chose X over Y because Z>" --meta '{"type": "decision"}'`
- **User preference**: `memori store "<preference>" --meta '{"type": "preference"}'`
- **Architecture insight** (saves 10+ min next session): `memori store "<how X works>" --meta '{"type": "architecture"}'`
- **Reusable pattern** (2+ instances): `memori store "<when X, do Y because Z>" --meta '{"type": "pattern"}'`
- **Unfinished work**: `memori store "<remaining tasks + context>" --meta '{"type": "roadmap"}'`

Types: `debugging`, `decision`, `architecture`, `pattern`, `preference`, `fact`, `roadmap`, `temporary`

**Don't store**: facts in CLAUDE.md/README, session-specific state, trivially re-discoverable info, uncertain information.

### When to Search

- **Before investigating a bug**: `memori search --text "<error or area>"`
- **Before designing**: `memori search --text "<component>"` or `--filter '{"type": "architecture"}'`
- **Before deep-diving into unfamiliar code**: `memori search --text "<subsystem>"`

### Side Effects

- `get`, `search`, `context`, `related` bump access_count on returned memories (affects decay ranking)
- `tag` and `update --meta` re-embed the vector (may prevent future dedup against this memory)
- `purge --confirm` and `delete` are irreversible
- `store` with dedup match updates existing memory's content but not access_count

### Reading Results

- Search results are hybrid-ranked (RRF fusion) -- trust ordering, not absolute score values
- Zero results? Broaden keywords, drop filters, or `memori list --type <type>` to browse
- In `context` output: "Stale" = not accessed in 30+ days (review candidates), "Frequent" = high access count

### Self-Maintenance

- Wrong memory? Update or delete immediately -- stale memories are worse than none
- 50+ memories? Check `memori stats` type distribution -- if one type >60%, tighten that trigger
- Scratch buildup? `memori purge --type temporary` (previews first, `--confirm` to delete)

### Key Commands

Run `memori <cmd> --help` for full details and examples on any command.

| Command | Purpose |
|---------|---------|
| `memori context "<topic>"` | Load relevant + recent + stale memories + stats |
| `memori store "<text>" --meta '{"type": "..."}'` | Store with typed metadata (auto-embeds, auto-dedup) |
| `memori search --text "<query>"` | Hybrid search (or `--filter`, `--text-only`, `--before/--after`) |
| `memori tag <id> key=value ...` | Merge typed tags (int/float/bool auto-coerced) |
| `memori update <id> --content/--meta` | Correct or enrich (merge default, `--replace` for full swap) |
| `memori delete <id>` / `memori purge` | Remove single / bulk delete with preview |
| `memori stats` / `memori embed` / `memori gc` | DB health, backfill embeddings, compact |
| `memori export > backup.jsonl` | JSONL backup (always JSONL regardless of --json flag) |
<!-- memori:end v0.6.0 -->
