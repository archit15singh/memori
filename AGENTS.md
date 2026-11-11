# Repository Guidelines

## Project Structure & Module Organization

Lorevell combines a Rust SQLite memory engine with PyO3 bindings and a Python CLI. `lorevell-core/src/` contains storage, search, embeddings, schema migrations, and shared types. `lorevell-python/src/lib.rs` exposes the Python API; `lorevell-python/python/lorevell_cli/` implements commands and bundles shared agent skills in `data/`. Rust integration tests live in `lorevell-core/tests/`, Python and CLI tests in `lorevell-python/tests/`, and Criterion benchmarks in `lorevell-core/benches/`. See `docs/` for architecture diagrams and packaging notes, and `CLAUDE.md` for detailed implementation constraints.

## Build, Test, and Development Commands

Run Rust commands from the repository root:

- `cargo build --workspace` builds both crates.
- `cargo fmt --all -- --check` checks Rust formatting.
- `cargo clippy --workspace --all-targets -- -D warnings` runs the CI lint checks.
- `cargo test -p lorevell-core --release` runs core tests.
- `cargo bench -p lorevell-core --bench vector_ops_bench` runs vector microbenchmarks.

For Python development, activate a virtual environment, install `maturin` and `pytest`, then run `maturin develop --release` from `lorevell-python/`. From the root, run `pytest lorevell-python/tests/test_lorevell.py lorevell-python/tests/test_cli.py -v`. Ensure the environment's `lorevell` executable is first on `PATH` so CLI tests exercise your source build.

## Coding Style & Naming Conventions

Follow existing four-space indentation in Rust and Python; use rustfmt for Rust layout. Use `snake_case` for functions and modules and `PascalCase` for Rust types and Python classes. CLI handlers follow `cmd_<name>` and are registered with argparse. Keep database logic in the Rust core and update Python conversions when shared types change. No Python formatter or linter is currently configured.

## Testing Guidelines

Use Rust's built-in test framework and pytest. Name Python files and functions `test_*`; use descriptive Rust test names. Prefer real SQLite databases: in-memory helpers for Rust and pytest `tmp_path` for Python. Add regression coverage for changed behavior, including CLI output and exit codes. No numeric coverage threshold is configured. Embedding tests may download model files.

## Commit & Pull Request Guidelines

History commonly uses Conventional Commits, such as `docs(readme): ...`, `ci(release): ...`, and `chore(release): ...`. Keep commits focused. PRs should explain the behavior or documentation change, link relevant issues, and report validation results. Include screenshots for dashboard changes and compatibility notes for API or schema changes. Run the applicable CI checks before requesting review.
