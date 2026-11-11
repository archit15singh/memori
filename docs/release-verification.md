# Real-project release verification

This evaluation uses Lorevell itself, a public real project, rather than the earlier synthetic retry/SQLite demos. Source-grounded maintainer knowledge was curated from commit `9dd899af947b9261f0de7058fecbdd421bd769ff`. No personal vault, private project or credential content was used. Raw authenticated agent logs remain local; the public corpus, frozen labels, result reports and Git evidence are checked in.

## Frozen retrieval evaluation

Twenty maintainer questions were frozen before evaluation and consolidation, outside the dream vault. The label file SHA256 is `e84a271c211623f587894480694227f48259e5acca728ece66efcae381fe0985`. Labels identify relevant stable note IDs; no model judged the answers. Initial corpus: 24 manually curated atomic notes, each citing public source. Learning added one verified procedure, making 25 active notes.

| Stage | Notes | Mode | Relevant top-1 | Relevant in top-3 | MRR@3 |
| --- | ---: | --- | ---: | ---: | ---: |
| Original search | 24 | Hybrid | 16/20 | 18/20 | 0.8500 |
| Original search | 24 | Keyword | 0/20 | 0/20 | 0.0000 |
| Empty-query-result fallback | 24 | Hybrid | 16/20 | 19/20 | 0.8667 |
| Empty-query-result fallback | 24 | Keyword | 15/20 | 18/20 | 0.8167 |
| After actual learning | 25 | Hybrid | 17/20 | 19/20 | 0.8917 |
| After actual learning | 25 | Keyword | 14/20 | 19/20 | 0.8083 |
| After actual dream | 25 | Hybrid | 17/20 | 18/20 | 0.8750 |
| After actual dream | 25 | Keyword | 15/20 | 19/20 | 0.8250 |

The search change is a deterministic any-term FTS fallback only when all-term matching returns zero filtered rows. It preserves literal escaping, metadata filters and successful strict results. A regression test covers the user-facing full-sentence query, filter retention and strict-match precedence. This improves this small acceptance set; it is not a learned ranker or broad quality claim.

Dream reconciled two release notes. It improved keyword top-1 on the learned corpus but reduced hybrid top-3 from 19 to 18: **consolidation does not guarantee better retrieval**. A paraphrase asking for notes “that point to this procedure” still misses the labeled backlinks note in the top three. The evidence-deletion question retrieves related archive/batch/rollback notes instead of the single labeled scope-validation note. Do not claim perfect recall, semantic truth, generated-answer accuracy, statistical significance, or generalization to other projects. The same maintainer authored notes and labels; this is an acceptance probe, not a blind benchmark.

Reproduce the final corpus results with an installed source build or package:

```bash
python -c 'from pathlib import Path; import shutil; p=Path(".venv/eval-vault"); p.mkdir(parents=True, exist_ok=True); [shutil.copy2(f,p/f.name) for f in Path("docs/evals/real-project/after").glob("*.md")]'
python scripts/eval-project.py --vault .venv/eval-vault --questions docs/evals/real-project/questions.json
python scripts/eval-project.py --vault .venv/eval-vault --questions docs/evals/real-project/questions.json --text-only
```

Use a new directory for each corpus. `before/` reproduces the 24-note fallback stage, `pre-dream/` the actual learned state, and `after/` the actual consolidated state. Baseline reports preserve the original search behavior; reproducing that behavior requires the source commit before the fallback change.

## Actual learning and independent recall

An authenticated, ephemeral Codex invocation inspected the actual release workflow and fixed a real defect: `always()` allowed the GitHub release announcement after registry failures. It removed that override, retained both registry dependencies and the tag condition, and verified those properties with PyYAML BaseLoader assertions. It searched existing knowledge, saved one procedure through the installed Lorevell CLI/skill and read it back: note `437fbf7d-859a-4e15-8def-6f4a1f14f6a4`.

A separate fresh Codex invocation was asked how to prevent the announcement failure, without the note ID or remedy in its prompt, and without reading source, previous logs or question labels. The first attempt failed to open the SQLite cache because the external vault was outside its writable workspace. A fresh invocation with the exact vault supplied using ordinary `--add-dir` retrieved the learned note and historical defect context, reported the correct gate and actual static verification, and explicitly stated that it had not run GitHub Actions or uploaded a registry artifact. No permission bypass flag was used.

This is external-memory learning across sessions, not model-weight training. Source and installed-skill use was real; no fake runtime substituted for Codex. Claude Code was not installed and is not claimed as a live authenticated test.

## Actual consolidation, rollback and repeat-run behavior

`lorevell dream --agent codex --max-notes 40 --timeout 600` processed all 25 actual notes. It reconciled the historical release defect with the verified procedure, retained their stable IDs and verification limits, and validated all 26 links. It changed two Markdown files, removed none, and left 25 active notes. No archiving was needed because no note was removed or superseded by a merge.

- Baseline: `a69d13d8bac0b5626b18dd923320692da9b15f77`.
- Consolidation: `2030846566e2bfc9931e8f9848189dd5014723db`.
- Actual `git revert` rollback: `01b92f0477ca3af206707e1cfb143ca141a67380`.
- Actual revert-of-rollback: `25761de61c9224d3e9f761953a3caafe692569fb`.

Reindexing after rollback restored exactly the complete pre-dream path set and SHA256 bytes; reapplying restored the exact after state. The dedicated vault was clean. A subsequent dream returned `unchanged`, no candidates, and invoked no agent. These commits belong to the local dedicated evaluation vault, not the product repository. [Structured record](evals/real-project/dream.json).

## Packaging and release gates

Local verification used Python 3.13 and Rust 1.99.1: 95 Rust tests, 24 no-embedding checks and 87 Python tests passed, along with formatting, Clippy and packaged-skill equality. The full source distribution built a wheel successfully; a Rust registry dry run packaged, compiled and stopped before upload. The earlier unsupported Rust 1.74 minimum claim was removed rather than promising an untested toolchain. Release CI uses stable Rust.

The release workflow validates source/tests, builds and clean-install-smokes wheels on Linux x64/ARM64, macOS Intel/ARM64 and Windows x64, and separately builds from the source distribution. Only successful artifact jobs permit registry publication. The GitHub announcement depends on both registry uploads succeeding. Existing GitHub Actions secrets are consumed only in the publishing jobs; no secret values are fetched locally or included in evidence. Manual dispatch builds/verifies without publishing; version tags enable publication. Supported runner labels were checked against [GitHub's image catalog](https://github.com/actions/runner-images).

Publication remains unverified until the registry artifacts and fresh registry installs have been inspected. Final registry evidence will be recorded after the actual release run; a successful local build alone is not a published release.
