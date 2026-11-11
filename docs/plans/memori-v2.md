> Historical Memori 2.0 record, preserved under its original names. Current commands and package names are documented in [the rename guide](../rebrand.md).

# Memori 2.0 implementation plan

Status: implementation and local verification complete. Delivery and CI state are tracked by the feature branch pull request. Breaking replacement authorized; all work stays on `feat/memori-v2`.

## Contract

Markdown is authoritative. One Rust `Vault` module translates YAML-frontmatter notes into the existing SQLite/FTS/vector engine. SQLite and graph tables are disposable cache. Explicit wiki links derive backlinks; graph expansion is one hop with an overall neighbor limit. Files under `archive/` remain evidence but leave active retrieval. Agents own interpretation, learning and consolidation.

The 2.0 CLI uses an explicit `--vault` directory (or `MEMORI_VAULT`, default `./memory`): add, search, show, index, update, archive, setup and dream. A legacy database is never silently opened or migrated. The existing low-level Rust search engine remains reusable; the public product interface becomes vault-first.

Notes need an `id`; type and tags are optional. Stable IDs or unambiguous relative file stems resolve wiki links. Broken/ambiguous links are diagnostics. Duplicate IDs and malformed notes fail indexing without changing the previous index. Atomic file replacements preserve original files on write failure. A process-visible vault lock serializes Memori writes/indexing; native editors remain independent and users reindex after edits.

## Slices and completion evidence

1. **Vault and derived index** — YAML parsing, atomic note mutations, content hashes and incremental synchronization, deletion/archive detection, rebuild. Prove manual edits and renames become searchable and deleting the cache loses no notes. Test failure atomicity and duplicate IDs.
2. **Explicit graph** — parse wiki links, resolve IDs/path stems, derive backlinks, expose bounded one-hop context. Test cycles, ambiguity, broken links, archived notes and bounded expansion through the public interface.
3. **CLI and learning skill** — native Python Vault binding; minimal vault-first commands; package one shared memory skill and install locally for Claude/Codex on explicit setup. Test real command processes across sessions, human/JSON output and error exits.
4. **Dream** — thin single-agent subprocess launcher; bounded changed-note manifest since the prior successful snapshot; preserve originals/archive evidence; validate/reindex before scoped Git commit; never advance checkpoint on failure. Test launcher contracts, failure paths, independent edits and real headless Codex execution on synthetic Git vaults. Claude availability is checked separately.
5. **Release and review** — versions 2.0.0, updated installation/architecture docs and CI; held-out retrieval experiment before/after real consolidation; all applicable Rust/Python checks; review complete diff. Open a new PR with Mermaid diagrams, exact evidence and limitations. No merge or release publication.

## Scope discipline

No session recorder, custom LLM API, orchestration framework, scheduler, graph database, learned ranking or skill generator. `dream` runs one existing installed agent under its normal permissions; deterministic validation and Git bookkeeping stay in Memori. Intelligence is instructions, not another model pipeline. Runtime selection is explicit (`--agent codex|claude`). Git history makes successful changes reversible; failed agent edits remain inspectable rather than being destructively reset.

## Progress

- [x] Vault/index and graph tested
- [x] Vault-first CLI and skills tested
- [x] Dream launcher tested, including real headless workflow
- [x] Held-out evaluation and complete checks recorded
- [x] Version/docs and package installation reviewed
