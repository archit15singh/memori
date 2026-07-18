# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.7.0] — 2026-07-18

### Added
- **PyPI release** — `py-memori` package with pre-built wheels for Linux, macOS (Intel + Apple Silicon), and Windows, Python 3.9–3.13.
- **crates.io release** — `memori-ai-core` Rust crate with full metadata (repository, homepage, documentation, keywords, categories).
- **CI workflow** (`.github/workflows/ci.yml`) — `cargo fmt --check`, `cargo clippy`, `cargo test`, `maturin develop`, `pytest` on push and PR.
- **Release workflow** (`.github/workflows/release.yml`) — tag-triggered, matrix-build wheels via `maturin-action`, automatic crates.io + PyPI upload.
- **`CHANGELOG.md`** — retroactive entries for v0.1 through v0.7.
- **`memori-core/README.md`** — project-level readme for crates.io/docs.rs.
- Crate-level `#![doc]` doc-comment on `memori-core/src/lib.rs` — feeds the docs.rs landing page.
- README badges (PyPI, crates.io, CI, license, Python, Rust), blog post links, and expanded PyPI classifiers.

### Changed
- **Package renamed:** `memori` → `py-memori` (PyPI, both naming-collision and "too similar to memori" rejection) and `memori-core` → `memori-ai-core` (crates.io) due to namespace collisions on both registries.
- **Import names unchanged:** Python `import memori` / `import memori_cli` and Rust `use memori_core::...` still work — only the *distribution* name changed.
- **CLI command unchanged:** `memori` is still the binary name (`pip install py-memori` installs a `memori` script).
- **Development status** raised from `3 - Alpha` to `4 - Beta`.

### Fixed
- README install instructions no longer require Rust toolchain — `pip install py-memori` works out of the box.

## [0.6.0] — 2026-03

### Added
- 15 best-practice fixes across CLI, docs, and DX.
- ~130 CLI integration tests (full subprocess-based matrix for all 18 subcommands).
- Architecture diagrams (engine + agent views) in `docs/`.

## [0.5.1] — 2026-03

### Added
- Prefix ID resolution (6+ chars on every ID-based command).
- Access-weighted decay scoring (logarithmic access boost + exponential time decay, ~69-day half-life).
- `memori related` command — semantic neighbors by vector similarity.
- Introspection bug fixes for `stats` / `count`.

## [0.5.0] — 2026-02

### Added
- `memori ui` — single-file web dashboard with Chart.js + D3 force-directed graph.

## [0.4.0] — 2026-02

### Added
- Comprehensive benchmark suite (Criterion.rs): search, CRUD, vector ops, embed, memory.
- File-size and write-throughput benchmarks at 1K–1M scale.

## [0.3.1] — 2026-02

### Added
- DX polish for Claude Code agent usage.

## [0.3.0] — 2026-02

### Added
- Auto-embeddings via fastembed (AllMiniLM-L6-V2).
- Cosine-similarity deduplication.
- Access tracking (`access_count`, `last_accessed`).
- Schema migrations via `PRAGMA user_version`.

## [0.2.0] — 2026-01

### Added
- Initial release: persistent memory for AI coding agents.
- SQLite with FTS5 full-text search.
- Memori facade struct with CRUD + search.

[0.7.0]: https://github.com/archit15singh/memori/releases/tag/v0.7.0
[0.6.0]: https://github.com/archit15singh/memori/releases/tag/v0.6.0
[0.5.1]: https://github.com/archit15singh/memori/releases/tag/v0.5.1
[0.5.0]: https://github.com/archit15singh/memori/releases/tag/v0.5.0
[0.4.0]: https://github.com/archit15singh/memori/releases/tag/v0.4.0
[0.3.1]: https://github.com/archit15singh/memori/releases/tag/v0.3.1
[0.3.0]: https://github.com/archit15singh/memori/releases/tag/v0.3.0
[0.2.0]: https://github.com/archit15singh/memori/releases/tag/v0.2.0