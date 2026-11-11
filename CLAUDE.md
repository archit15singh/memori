# Lorevell contributor guide

Lorevell 2.0 is a Markdown knowledge vault with a disposable SQLite search index. Existing Claude Code/Codex runtimes do learning and consolidation. Read README.md and docs/v2.md for the current product contract; docs/plans/memori-v2.md records the implementation scope.

## Build and verify

```bash
cargo fmt --all -- --check
cargo clippy --workspace --all-targets -- -D warnings
cargo test -p lorevell-core --release
cargo test -p lorevell-core --no-default-features --release --test vault_test --test relevance_test --test freshness_test
python3 scripts/sync-skills.py --check
# First create .venv with maturin and pytest, using a supported Python interpreter.
(cd lorevell-python && VIRTUAL_ENV="$PWD/../.venv" ../.venv/bin/maturin develop --release)
PATH="$PWD/.venv/bin:$PATH" .venv/bin/python -m pytest lorevell-python/tests -v
```

Tests use disposable files and real SQLite. CLI tests launch the environment's actual installed `lorevell`; rebuilding the native extension is required after Rust changes. Some tests initialize/download the embedding model. Headless runtime contract tests use controlled subprocesses; they do not establish real agent behavior. Keep live authenticated runs separate and record their actual outcomes and limitations.

## Module ownership

| Path | Responsibility |
| --- | --- |
| `lorevell-core/src/vault.rs` | Canonical Markdown parsing, writes, archives, hash indexing and explicit graph |
| `lorevell-core/src/search.rs` | Existing FTS5/vector/RRF retrieval and semantic gate |
| `lorevell-core/src/storage.rs` | Low-level SQLite engine operations, retained as retrieval plumbing |
| `lorevell-core/src/schema.rs` | Base v4 migrations and vault-only cache tables |
| `lorevell-core/src/embed.rs` | Lazy AllMiniLM-L6-V2 singleton; keep independent of vault policy |
| `lorevell-core/src/types.rs` | Shared engine records, queries and errors |
| `lorevell-python/src/lib.rs` | PyO3 conversion, `PyVault` and low-level `PyLorevell` binding |
| `lorevell-python/python/lorevell_cli/__init__.py` | Vault-first argparse commands and explicit local skill installation |
| `lorevell-python/python/lorevell_cli/dream.py` | One subprocess, batch checkpoint, validation and scoped Git finalization |
| `skills/lorevell/SKILL.md`, `skills/dream/SKILL.md` | Canonical shared agent behavior |

`python3 scripts/sync-skills.py` refreshes the two packaged skill copies. CI checks equality. Keep the source and packaged forms identical; installed wheels need the packaged files.

## Invariants

- Markdown is authoritative. Index loss must not lose knowledge or links. An index row never justifies silently overwriting a similar note.
- Parse/validate the complete active file set before changing cached rows. Preserve the old index on failure. File writes are atomic per file; no cross-filesystem/database transaction is implied.
- IDs are stable; filenames may change. Derive backlinks from declared wiki links. Report missing/ambiguous links. Graph context is one hop, separately labeled and globally bounded per search.
- `archive/` preserves original bytes and is excluded from active indexing. Hidden paths and symlinks do not extend the vault scope.
- Native editor writes do not acquire Lorevell locks. Document this limitation; do not claim general concurrent edit/merge guarantees.
- Dream uses a dedicated Git root and one installed headless agent. Preserve normal runtime permissions. Structural validation cannot prove retained semantic meaning.
- Commit/checkpoint only a successful validated batch. Failures retain inspectable edits and leave acknowledgement unchanged. Pending candidates remain pending.
- Do not add a model API, scheduler, event journal, orchestration framework or graph database to implement intelligence already provided by the agent.

## Retrieval details worth preserving

FTS5 external-content indexing uses `rowid` and metadata-aware triggers; its stored text includes raw JSON keys. Vectors are native-endian f32 BLOBs. Explicit supplied vectors bypass automatic embedding. The default model has 384 dimensions. The raw cosine gate is inclusive and precedes age/use adjustment. Hybrid literal matches remain eligible below that floor. RRF takes up to `3 * limit` candidates per leg and uses fallback rank `candidate_limit + 1` for a missing leg; returned scores are not probabilities.

The low-level engine still exposes its database-only clocks and methods for library consumers/tests. They are not a second canonical vault store. Keep API conversions in sync when shared Rust types change.

## Changes and release

This is a breaking 2.0 interface: no automatic personal DB migration, old dashboard, snippet injection or compatibility CLI. Reuse the engine while keeping the user-facing workflow coherent. Update README.md, this guide and affected operational docs when behavior changes. Run relevant checks before a PR; describe behavior, migration implications, evidence and limits. A PR request does not authorize merging or publishing a release.
