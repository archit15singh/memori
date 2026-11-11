# Eval-gated improvement loops

Base source: `e990dce4e88991dc47c71d40baaeb9cada0a28ce` (PR #12). The corpus stays at the same 25 public project notes in `../real-project/after/`. Neither candidate edits the knowledge or labels. The original 20 questions were frozen before the earlier evaluation; 10 additional maintainer paraphrases were frozen before these candidate experiments. SHA256 of the additional set: `e311e04ac32606ac4dd6af705f7dc99eed6fbd80a41ff7032d1997b30ad6e2c3`.

These are small, self-authored English acceptance sets, not a blind benchmark. We do not claim statistical significance, semantic truth or multilingual quality. Reports preserve all candidate outputs, including rejected changes.

## Decision gate

For both question sets in hybrid and keyword modes: preserve question hashes, question counts and mode; improve at least one of top-1 count, top-3 hit count or MRR@3; regress none. Run the source tests before opening/merging the change. A gain on the main questions cannot excuse a shadow-set regression. Single-report gates are supplemented by repeated runs to expose ranking instability.

`python scripts/gate-eval.py <baseline.json> <candidate.json> ...` prints a structured decision and returns nonzero on rejection. The actual zero-gain RRF/pool candidates are rejected, as is the earlier real dream ranking regression in `known-regression-gate.json`; it is not a gate that always passes.

| Candidate | Implementation | Decision |
| --- | --- | --- |
| Zero missing-leg RRF contributions | Replace the existing fallback rank with zero contribution | Rejected: no measured change on either hybrid set |
| Five-times candidate pool | Increase each hybrid leg from 3× to 5× requested limit | Rejected: no measured gain, more candidates |
| Built-in Porter stemming | SQLite Porter tokenizer over Unicode61, transactional v4→v5 FTS-only rebuild | Accepted by gate; English word forms improve keyword recall and hybrid top-3 |

## Porter results

Top-3 means at least one of the manually labeled relevant note IDs appears in the first three. It is not answer correctness or classical multi-document recall.

| Set / mode | Before top-1 | After top-1 | Before top-3 | After top-3 | Before MRR@3 | After MRR@3 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Main / hybrid | 17/20 | 17/20 | 18/20 | 19/20 | .8750 | .8917 |
| Main / keyword | 15/20 | 18/20 | 19/20 | 19/20 | .8250 | .9167 |
| Shadow / hybrid | 9/10 | 9/10 | 10/10 | 10/10 | .9500 | .9500 |
| Shadow / keyword | 7/10 | 9/10 | 9/10 | 9/10 | .8000 | .9000 |

The earlier fresh-cache probe happened to score main hybrid top-1 at 18/20; the production migration run scored 17/20. Repeated evaluation found a real reason not to cherry-pick that difference: hash-map iteration can change the order of equal RRF scores. Across ten hybrid runs, baseline main top-1 averaged 16.8/20 and Porter averaged 17.1/20; main top-3 stayed 18/20 versus 19/20. Shadow hybrid stayed 9/10 top-1 and 10/10 top-3. Six baseline main questions and four Porter main questions had varying returned ID order. Raw repeated reports are retained. Deterministic tie-breaking is being evaluated separately; it is not silently included in the stemming change.

The v4 migration retains vectors, metadata terms, IDs, timestamps, access counts, and subsequent update/delete trigger behavior; repeated opens are idempotent. Regression tests demonstrate the actual old tokenizer miss on metadata `backups` queried as `backup`, then matching after migration. Accented Latin and CJK probes plus metadata filters pass. Local validation: 97 Rust tests, 25 no-embedding checks, 87 Python tests, formatting, Clippy and skill-copy equality.

Reproduce the Porter gate after building this checkout, using the same reports as the committed evidence:

```bash
python scripts/gate-eval.py \
  docs/evals/loops/baseline-main-hybrid.json docs/evals/loops/porter-migrated-main-hybrid.json \
  docs/evals/loops/baseline-main-text.json docs/evals/loops/porter-migrated-main-text.json \
  docs/evals/loops/baseline-shadow-hybrid.json docs/evals/loops/porter-migrated-shadow-hybrid.json \
  docs/evals/loops/baseline-shadow-text.json docs/evals/loops/porter-migrated-shadow-text.json
```

To regenerate retrieval reports, use `scripts/eval-project.py` with a fresh copy of `docs/evals/real-project/after/`, selecting `questions.json` or `shadow-questions.json`, and optionally `--text-only`. Timing-sensitive clocks and model/runtime versions can affect rankings; the stored output is evidence of these runs rather than a promise of identical future rankings.
