> Historical Memori 2.0 record, preserved under its original names. Current commands and package names are documented in [the rename guide](../docs/rebrand.md).

# Memori 2.0 verification

Observed locally on 12 November 2026, macOS arm64, Python 3.13, source-built native extension. This report separates executable contracts, real agent behavior and limitations. It is not a production quality benchmark.

## Markdown, index and graph

Rust public-vault tests and actual Python CLI subprocesses exercise manual edits, hash synchronization, renames, source removal, complete cache loss/rebuild, malformed-note and duplicate-ID rejection without cache loss, stable identities, metadata mutation, byte-preserving archives, wiki aliases/anchors, cycles, ambiguous/missing targets, backlinks and bounded one-hop expansion. The existing low-level engine regressions remain, including builds without embeddings. CLI and native API checks use real SQLite and files, not a parallel mock implementation.

## Real learning and independent recall

A headless Codex session was given a synthetic Python SQLite replacement function whose failing batch lost the original rows. Before intervention, its executable check failed with `failed batch lost the original rows`.

The agent diagnosed the transaction boundary, wrapped the DELETE/INSERT sequence in `with connection:`, and ran the check successfully:

```text
PASS: failed batch preserves original rows; successful batch commits replacement
```

It then used the installed Memori CLI and shared learning skill to save a procedural note, including cause, remedy, verification and limits. A separate headless Codex invocation was asked to recall the procedure using only the vault, without opening the source or prior session log. It retrieved note `b879d311-f2b0-4bb1-8d47-f21c051f2189` and reported the correct transaction remedy, `python3 transaction_demo.py` verification command, and in-memory/default-transaction scope. The retained [learning note](evals/v2-learning-note.md) records the evidence. The test demonstrates persistence and recall across independent sessions; it does not show model-weight training.

## Real dream and held-out check

A dedicated temporary Git vault held two complementary, partly redundant HTTP-retry notes and one unrelated cooking note. The [before fixture](evals/v2-before/) contains the exact source texts. Five query labels in [v2-held-out.json](evals/v2-held-out.json) were frozen outside the vault and evaluated before launching the consolidator. They were not supplied to its prompt.

`memori dream --agent codex --max-notes 10 --timeout 360` invoked the actual installed Codex CLI. It consolidated the retry procedure, removed redundancy, retained the original investigation byte-for-byte under `archive/`, preserved its stable ID in that evidence file, and linked the retained procedure to the archived source. Memori validated the vault, reindexed it and created a scoped Git consolidation commit. The unrelated cooking note was unchanged. The [after fixture](evals/v2-after/) contains the resulting files.

| Measure | Before | After |
| --- | ---: | ---: |
| Questions whose top retrieved note contained every required fact | 2 / 5 | 5 / 5 |
| Original investigation preserved byte-for-byte | Yes | Yes, archived |
| Unrelated cooking note changed | No | No |

The metric checks labeled required terms in the top retrieved note, with `graph_limit=0`. It measures useful completeness after consolidation rather than classic precision/recall or semantic truth. The queries are held out from this one consolidation run; they and the corpus are tiny synthetic fixtures, with deliberate opportunities for complementary-note merging. The seeded retry claims were input evidence, not newly verified production behavior. No universal retrieval improvement is inferred.

The local vault's baseline was `9df6a56124e93cb6e9bcdf2f6ab670d261a29000`; consolidation was `c2965175ef3a6d3ecf6a6aca3ba040457203ef9b`. These identify the disposable acceptance vault, not commits in this source repository. The committed before/after snapshots and [machine-readable results](evals/v2-result.json) make the observations inspectable. Reproduce retrieval against either snapshot with:

```bash
.venv/bin/python scripts/eval-vault.py --vault docs/evals/v2-before
.venv/bin/python scripts/eval-vault.py --vault docs/evals/v2-after
```

A second real `memori dream --agent codex` invocation returned `status: unchanged`, with no candidates and no agent invocation. Launcher tests separately verify incremental batches, pending work, baseline snapshots, successful commit, ordinary Git revert + reindex, failed processes, timeouts, invalid notes, unpreserved deletion, unrelated edits and missing runtime handling. Those controlled subprocess tests are not claimed as real model behavior.

## Final gate

The final local gate passed:

| Check | Result |
| --- | --- |
| `cargo build --workspace` | Passed |
| `cargo fmt --all -- --check` | Passed |
| `cargo clippy --workspace --all-targets -- -D warnings` | Passed |
| Core Rust tests | 94 passed |
| Vault/relevance/freshness without embeddings | 24 passed (feature rerun) |
| Native Python / CLI / dream tests | 87 passed |
| Packaged skill equality and skill-creator validation | Passed |
| Built 2.0.0 wheel installed into a clean environment | Native vault, add/search and installed skills passed |
| Final native build on the committed evaluation snapshots | Required-fact completeness remained 2/5 → 5/5 |

The actual dream consolidation commit was also reverted with ordinary Git, followed by reindexing: the original active notes returned and the archive disappeared. Reverting that rollback and reindexing restored the consolidated procedure and byte-identical archived evidence. The synthetic vault was clean afterward. This tested rollback of the real agent-generated change, in addition to the controlled launcher regression.

## Limits

- The actual agent runs used Codex. Claude Code was not installed locally; its documented command construction, missing-runtime behavior and shared skill installation are covered, but no authenticated Claude execution is claimed.
- OS/Python release matrices, power-loss durability, large-vault performance, concurrent native editing and adversarial agent behavior were not exhaustively tested.
- Filesystem writes are atomic per note. Git preserves prior versions; there is no distributed or multi-file filesystem transaction.
- Dream's structural checks cannot prove semantic retention or factual correctness. Inspect important changes; no automatic scheduler or blanket trust in stored instructions is introduced.
- The 2.0 CLI is intentionally breaking. No old personal database was migrated, no release was published and no PR was merged during this work.
