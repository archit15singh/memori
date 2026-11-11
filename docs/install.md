# Install Lorevell 2.0

Follow the [source-build instructions](../README.md#install-from-this-checkout) in the repository README. This branch prepares version 2.0.0; it does not publish wheels, install globally, migrate the old personal database or reconfigure an agent automatically.

Create an isolated Python environment, install `maturin`, and run `maturin develop --release` in `lorevell-python`. Put that environment's `bin` directory first on `PATH`. Verify `lorevell --version` reports 2.0.0 and `lorevell --help` lists the vault-first commands.

For literal-only operation:

```bash
lorevell --vault ./knowledge init
lorevell --vault ./knowledge add 'A reusable lesson with evidence.' --text-only
lorevell --vault ./knowledge search 'lesson' --text-only
```

For semantic search, omit `--text-only`; the model may download on first use. Use a disposable vault to verify a new installation, not an existing personal database.

Install project-local agent skills explicitly with `lorevell setup --agent codex --project <project>` or the corresponding `claude` command. Dream uses the existing installed runtime and its authentication. An unavailable runtime is an actionable error; no runtime is downloaded or alternate provider silently chosen. Claude Code is optional for users who select Codex, and vice versa.

For dream, initialize a dedicated Git repository at the vault root (`lorevell init` does this), configure your normal Git identity, resolve unrelated dirty files and inspect `lorevell dream --agent codex --dry-run` before a first run. See [the operational design](v2.md) for snapshots, checkpoints and rollback.
