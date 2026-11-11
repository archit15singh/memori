# Relevance in 2.0

`lorevell search "topic"` uses the existing Rust hybrid retrieval engine. FTS5 matches literal text (including metadata); MiniLM supplies cosine candidates; RRF combines their sub-ranks. A score is an ordering aid, not confidence or factual truth.

```bash
lorevell search 'database architecture' --min-similarity 0.4
lorevell search 'database architecture' --text-only
lorevell search 'database architecture' --graph-limit 0
```

The optional inclusive cosine floor is a finite number in `[-1, 1]`. It gates raw cosine before age/use adjustment, truncation and RRF. Hybrid literal matches remain eligible below that floor. `--text-only` rejects a cosine floor because it has no semantic leg. No universal default cutoff is selected.

The native low-level `PyLorevell.search(vector=..., min_similarity=...)` and related-memory APIs remain tested. Thresholded queries reject invalid/zero vectors, skip incompatible stored vectors and accumulate cosine in f64. Pure vector scores remain age/use-adjusted cosine; hybrid scores remain RRF.

Vault search returns explicit linked `context` separately from ranked `matches`. A linked neighbor is not a cosine-qualified result. Graph expansion is one hop and bounded by an overall note count; metadata filters still apply.

The old native engine calibration remains runnable with `scripts/eval-relevance.py`. The 2.0 experiment uses `scripts/eval-vault.py` and [v2-held-out.json](evals/v2-held-out.json) to measure the required-fact completeness of top retrieved notes before and after consolidation. These are small synthetic fixtures, not held-out production benchmarks. See [the verification report](v2-verification.md) for actual results and limitations.
