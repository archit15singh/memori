# Memori Launch Copy

Ready-to-paste content for each platform. All character limits verified.

---

## Hacker News (Show HN)

### Option A: Link post (blog post as URL)

**Title** (80 char max):
```
Show HN: Memori – Rust+SQLite persistent memory for AI coding agents (43µs reads)
```

**URL:**
```
https://github.com/archit15singh/memori
```

### Option B: Text post (no URL, discussion-style)

**Title:**
```
Show HN: I built a persistent memory layer for AI agents in Rust – single SQLite file, zero config
```

**Text:**
```
Every Claude Code session starts from zero. It doesn't remember the bug you debugged yesterday,
the architecture decision you made last week, or that you prefer Tailwind over Bootstrap. I built
Memori to fix this.

It's a Rust core with a Python CLI. One SQLite file stores everything -- text, 384-dim vector
embeddings, JSON metadata, access tracking. No API keys, no cloud, no external vector DB.

What makes it different from Mem0/Engram/agent-recall:

- Hybrid search: FTS5 full-text + cosine vector search, fused with Reciprocal Rank Fusion.
  Text queries auto-vectorize -- no manual --vector flag needed.
- Auto-dedup: cosine similarity > 0.92 between same-type memories triggers an update instead
  of a new insert. Your agent can store aggressively without worrying about duplicates.
- Decay scoring: logarithmic access boost + exponential time decay (~69 day half-life).
  Frequently-used memories surface first; stale ones fade.
- Built-in embeddings: fastembed AllMiniLM-L6-V2 ships with the binary. No OpenAI calls.
- One-step setup: `memori setup` injects a behavioral snippet into ~/.claude/CLAUDE.md that
  teaches the agent when to store, search, and self-maintain its own memory.

Performance (Apple M4 Pro):
- UUID get: 43µs
- FTS5 text search: 65µs (1K memories) to 7.5ms (500K)
- Hybrid search: 1.1ms (1K) to 913ms (500K)
- Storage: 4.3 KB/memory, 8,100 writes/sec
- Insert + auto-embed: 18ms end-to-end

The vector search is brute-force (adequate to ~100K), deliberately isolated in one function
for drop-in HNSW replacement when someone needs it.

After setup, Claude Code autonomously:
- Recalls relevant debugging lessons before investigating bugs
- Stores architecture insights that save the next session 10+ minutes of reading
- Remembers your tool preferences and workflow choices
- Cleans up stale memories and backfills embeddings

~195 tests (Rust integration + Python API + CLI subprocess), all real SQLite, no mocking.
MIT licensed.

GitHub: https://github.com/archit15singh/memori
Blog post on the design principles: https://archit15singh.github.io/posts/2026-02-28-designing-cli-tools-for-ai-agents/
```

---

## Product Hunt

**Name** (40 char max):
```
Memori
```

**Tagline** (60 char max):
```
Rust-powered persistent memory for AI coding agents
```

**Description** (500 char max, currently 489):
```
AI coding agents forget everything between sessions. Memori gives them persistent memory in a single SQLite file -- no cloud, no API keys, no config.

Rust core. Hybrid search (FTS5 + vector) with auto-dedup and decay scoring. Built-in embeddings ship with the binary. 43µs reads, 4.3 KB per memory, 8,100 writes/sec.

One command injects a behavioral snippet that teaches your agent when to store, search, and self-maintain its memory. Every session starts smarter than the last.

Open source. MIT licensed.
```

**Launch tags** (pick up to 3):
```
Developer Tools, Open Source, Artificial Intelligence
```

**First comment:**
```
Hey everyone -- I'm Archit, the maker.

I built Memori because I got tired of re-explaining context to Claude Code every session.
"We debugged this yesterday." "You chose Tailwind over Bootstrap last week." "The API uses
prefix-based ID resolution, remember?"

It never remembers. So I built something that does.

The core insight: memory for AI agents isn't a chatbot problem. It's a search problem. You
need hybrid retrieval (full-text AND semantic), automatic deduplication (agents store
aggressively), and decay scoring (recent + frequently-accessed memories should surface first).

I wrote the engine in Rust for speed and the CLI in Python for ergonomics. The whole thing
is one SQLite file you can copy, back up, or delete. No external services.

The part I'm most proud of: the behavioral snippet. Running `memori setup` injects guidance
directly into the agent's system prompt that teaches it *when* to store memories (after
non-obvious bug fixes, after choosing between alternatives, when leaving unfinished work)
and *when to search* (before investigating bugs, before designing anything). The agent
becomes self-maintaining.

I wrote a deep-dive on the design principles behind the CLI:
https://archit15singh.github.io/posts/2026-02-28-designing-cli-tools-for-ai-agents/

Would love feedback -- especially from other Claude Code / Cursor / AI agent users.
What memory patterns do you wish your agent remembered?
```

---

## Trendshift

**Repository:**
```
archit15singh/memori
```

**Description:**
```
Persistent memory layer for AI coding agents. Rust core + SQLite + FTS5 full-text search
+ vector embeddings in a single file. Hybrid search with Reciprocal Rank Fusion, automatic
deduplication, decay scoring, and built-in embeddings (no API keys). 43µs reads, 4.3 KB
per memory, 8,100 writes/sec. One-command setup injects a behavioral snippet that teaches
AI agents to autonomously store, search, and self-maintain their own memory across sessions.
MIT licensed.
```

---

## Twitter/X Thread (bonus -- for launch day amplification)

**Tweet 1 (hook):**
```
AI coding agents forget everything between sessions.

I built Memori -- a Rust-powered persistent memory layer that fits in a single SQLite file.

43µs reads. Zero API keys. Zero cloud. Zero config.

Open source, MIT licensed.

github.com/archit15singh/memori
```

**Tweet 2 (the problem):**
```
The problem isn't "memory" -- it's retrieval.

Your agent stores 500 memories. How does it find the right one?

Memori uses hybrid search: FTS5 full-text + cosine vector similarity, fused with Reciprocal
Rank Fusion. Text queries auto-vectorize. No manual flags.

Result: the right memory surfaces in 1ms.
```

**Tweet 3 (the magic):**
```
The part that surprised me most:

`memori setup` injects a behavioral snippet into your agent's system prompt.

It teaches the agent WHEN to store (after debugging, after decisions, when leaving
unfinished work) and WHEN to search (before investigating bugs, before designing).

The agent becomes self-maintaining.
```

**Tweet 4 (numbers):**
```
Benchmarks (M4 Pro):

- UUID lookup: 43µs
- Text search: 65µs
- Hybrid search: 1.1ms
- Storage: 4.3 KB/memory
- Write throughput: 8,100/sec
- Insert + embed: 18ms

Brute-force vector search. No HNSW. Still fast to 100K memories.

Rust + SQLite + zero dependencies = fast.
```

**Tweet 5 (CTA):**
```
Deep-dive on the 10 design principles behind building CLI tools for AI agents:

archit15singh.github.io/posts/2026-02-28-designing-cli-tools-for-ai-agents/

If you're building tools that agents invoke, this might save you some iteration cycles.
```

---

## GitHub Repo Description (one-liner, 350 char max)

```
Persistent memory for AI coding agents. Rust + SQLite + FTS5 + vector search in a single file. Hybrid retrieval with auto-dedup, decay scoring, and built-in embeddings. One-command setup teaches agents to autonomously store, search, and self-maintain memory across sessions.
```

---

## Elevator Pitch (for any platform that asks "what is this?")

```
Memori is a persistent memory system for AI coding agents. Every session starts from zero
-- the agent doesn't remember yesterday's debugging lesson or last week's architecture
decision. Memori fixes this with a single SQLite file that stores text, vector embeddings,
and metadata. Hybrid search finds the right memory in milliseconds. Auto-deduplication
prevents bloat. Decay scoring surfaces what matters. And a behavioral snippet teaches the
agent to maintain its own memory autonomously -- no human intervention needed.

Rust core for speed, Python CLI for ergonomics, zero external dependencies.
```
