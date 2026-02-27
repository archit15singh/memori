# Memori: Open Source Packaging & Star Strategy

## Context

Memori has strong fundamentals -- solid Rust core, good test coverage (94 tests), real benchmarks, thoughtful agent DX (prefix IDs, --raw output, setup command, decay scoring). But it's invisible: source-only install, no CI, no badges, no visuals, no distribution. The competitive landscape (Mem0 at 48K stars, Engram, agent-recall) shows what "packaged well" looks like.

## The Brainstorm -- 15 Ideas Ranked by Star Impact

---

### TIER 1: Unblock adoption (without these, nothing else matters)

**1. Publish to PyPI with pre-built wheels**
- Right now: requires Rust toolchain + maturin + git clone. 80%+ of visitors bounce here.
- After: `pip install memori` or `pipx install memori`. One command, works everywhere.
- How: maturin can build wheels for Linux/macOS/Windows. GitHub Actions + `maturin publish` on tag.
- This is the #1 blocker. Everything else is marketing on top of a locked door.

**2. MCP server**
- Every competitor has one (Engram, agent-recall, memories.sh, Mem0). MCP is now table stakes.
- Without it, memori is invisible to Cursor, Windsurf, Copilot, and the MCP server directory.
- The MCP directory is a discovery channel -- hundreds of thousands of weekly users browse it.
- Could be a thin wrapper: expose store/search/get/context/related as MCP tools.

**3. Add CI (GitHub Actions)**
- Zero CI today. No build badge, no test gate, no confidence signal for contributors.
- Minimum: `cargo test`, `cargo clippy`, `cargo fmt --check`, `maturin develop`, `pytest` on push/PR.
- Gets you the green "passing" badge which is the first thing OSS evaluators look for.

---

### TIER 2: First-impression conversion (README as landing page)

**4. Hero visual -- terminal recording or dashboard screenshot**
- The README is 100% text. Zero images. The dashboard exists (Chart.js + D3 force graphs) and is hidden.
- A 10-second asciinema GIF showing `store -> search -> context` would be the highest-ROI visual.
- Dashboard screenshot as a second visual showing the analytics/graph view.

**5. Restructure above-the-fold**
- Current: title -> technical description -> install (which is a wall of source-build steps)
- Better: punchy one-liner -> badges -> hero GIF -> "why this exists" bullets -> `pip install memori` -> 3-command quickstart
- The "After setup, Claude Code will automatically..." bullets are the best marketing copy in the README -- they're buried below the fold.

**6. Add a comparison table vs alternatives**
- memori has real differentiators that aren't being communicated:
  - Zero LLM dependency (Mem0 needs API calls for extraction)
  - Single file, zero config (Mem0 needs vector DB + graph DB)
  - Built-in hybrid search with RRF fusion (Engram has FTS5 only, no vectors)
  - Auto-dedup + decay scoring (unique in the space)
- A "Why Memori?" table against ChromaDB, Mem0, Engram would be free marketing.

**7. Add badges**
- License (MIT), PyPI version, crates.io, CI status, Python version, Rust
- Even static badges signal "this is a real project" vs. "someone's weekend hack"

---

### TIER 3: Distribution & discoverability

**8. Publish to crates.io**
- Missing: repository, keywords, categories, readme, homepage, documentation fields
- 5 minutes of Cargo.toml edits, then `cargo publish`
- Keywords: `sqlite`, `vector-search`, `ai-agent`, `memory`, `fts5`

**9. GitHub repo metadata**
- Set description: "Persistent memory for AI coding agents -- SQLite + vector search + FTS5 in a single binary"
- Set topics: `ai-agent`, `memory`, `sqlite`, `vector-search`, `claude-code`, `rust`, `embeddings`, `fts5`, `llm`, `developer-tools`
- This is literally clicking buttons on GitHub. Free discoverability.

**10. Launch strategy**
- "Show HN" post: average 289 stars in a week. "Rust + SQLite + zero-config memory for AI agents" is HN catnip.
- Reddit: /r/LocalLLaMA, /r/ClaudeAI, /r/MachineLearning
- Submit to awesome-lists: awesome-claude, awesome-vector-databases, awesome-rust, awesome-ai-tools
- MCP server directory listing (after building the MCP server)

---

### TIER 4: Polish & credibility

**11. CONTRIBUTING.md + issue/PR templates**
- Build instructions, test instructions, PR process
- Issue templates: bug report, feature request
- Signals "contributions welcome" to the OSS community

**12. Fix URL mismatch**
- README and pyproject.toml reference `archit-singhh/memori`, git remote is `archit-15dev/memori`
- Broken links = instant credibility loss

**13. Code quality cleanup**
- `cargo fmt` (formatting drift in benchmarks and schema.rs)
- `cargo clippy --fix` (21 warnings in memori-python)
- Add rustfmt.toml, .editorconfig
- These are prerequisites for CI (which will enforce them)

**14. CHANGELOG.md**
- Retroactive changelog for v0.1 through v0.5.1
- Users need this to evaluate upgrades. Also helps with release automation.

**15. Rust API docs (docs.rs readiness)**
- Most public functions lack `///` doc comments
- Crate-level `#![doc]` documentation missing
- docs.rs auto-generates from these -- currently would produce a sparse page

---

## What the Competition Does That We Don't

| Gap | Who Has It | Impact |
|-----|-----------|--------|
| MCP server | Engram, agent-recall, memories.sh, Mem0 | Very high -- discovery channel |
| pip install | Mem0, Letta, Graphiti | Very high -- adoption gate |
| Demo GIF | Most 1K+ star repos | High -- conversion |
| Comparison table | Mem0 (benchmarks vs OpenAI Memory) | High -- positioning |
| Multi-agent support | Mem0, Letta | Medium -- enterprise appeal |
| Knowledge graph | Graphiti, agent-recall, Cognee | Medium -- different paradigm |
| Cloud sync | memories.sh | Low -- niche |

## What We Have That They Don't

| Differentiator | vs Who |
|---|---|
| Zero LLM dependency for memory ops | vs Mem0, Graphiti, Cognee (all need LLM API calls) |
| Hybrid search with RRF fusion | vs Engram (FTS5 only), agent-recall (no vector) |
| Built-in embeddings (fastembed) | vs Engram (none), agent-recall (none) |
| Cosine-similarity auto-dedup | vs everyone (unique) |
| Decay scoring (access + time) | vs everyone (Mem0 has unused counter) |
| Rust performance + Python ergonomics | vs Go (Engram) or pure Python (Mem0/Letta) |
| Web dashboard with D3 graphs | vs Engram (TUI only), Mem0 (SaaS dashboard) |

## Execution Plan

### Wave 1: Weekend sprint -- unblock everything

- [ ] Fix URL mismatch (`archit-singhh` -> `archit-15dev` in README.md, pyproject.toml)
- [ ] GitHub repo description + topics (via `gh` CLI or GitHub UI)
- [ ] `cargo fmt` + `cargo clippy --fix`
- [ ] Add CI (GitHub Actions: `cargo test`, `clippy`, `fmt --check`, `maturin develop`, `pytest`)
- [ ] Add badges to README (CI, PyPI, license, Python version)
- [ ] Fill in Cargo.toml metadata (repository, keywords, categories for crates.io)
- [ ] Add rustfmt.toml, .editorconfig, LICENSE file

### Wave 2: Ship the package

- [ ] Publish to PyPI (maturin + GitHub Actions release workflow on tag)
- [ ] Publish to crates.io
- [ ] Restructure README above-the-fold (punchy one-liner, badges, "Why Memori?" bullets, `pip install`, 3-command quickstart)
- [ ] Add hero GIF (asciinema recording of `store -> search -> context`)
- [ ] Add dashboard screenshot
- [ ] Add comparison table (vs Mem0, Engram, agent-recall)

### Wave 3: Ecosystem play

- [ ] Build MCP server (thin wrapper: store/search/get/context/related as MCP tools)
- [ ] CONTRIBUTING.md + issue/PR templates
- [ ] CHANGELOG.md (retroactive for v0.1 through v0.5.1)
- [ ] Launch on HN, Reddit (/r/LocalLLaMA, /r/ClaudeAI), awesome-lists

### Wave 4: Depth

- [ ] Rust API docs (`///` doc comments, crate-level `#![doc]`) for docs.rs
- [ ] Examples/ directory
- [ ] Homebrew formula
- [ ] Multi-agent / workspace support
