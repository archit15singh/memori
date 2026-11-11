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

## Natural-language keyword queries

Literal FTS5 first requires all quoted query terms. If no filtered rows match and there is more than one term, it retries with quoted terms joined by OR, retaining the same metadata filter and ranking. This deterministic fallback applies to the text leg of hybrid retrieval too. It never interprets user tokens as FTS operators. Successful all-term results keep precedence; fallback scores are still rankings, not truth or confidence.

## English word forms

Schema v5 uses SQLite's built-in Porter tokenizer over Unicode61 so English variants such as `migration`/`migrating` and `backup`/`backups` can match. Opening a v4 database rebuilds only its derived FTS tokens in a transaction, retaining body and metadata terms, vectors and clocks. Existing wiki links and Markdown are unchanged. Escaping still treats query terms as data; text-only search is token-based, not byte-exact matching. This is English stemming, not multilingual semantic search; accented Latin and CJK literal probes are covered, but broad multilingual quality is unmeasured.

Equal hybrid RRF scores are ordered by semantic-leg rank, then stable note ID. This changes tie order only and makes repeated identical queries deterministic on the same index, clocks and model; it does not make scores probabilities or prevent changes after source/model updates.

A zero result limit does not initialize text embeddings. The CLI still validates and indexes Markdown, but skips embedding generation when `--limit 0` is requested. Positive-limit retrieval behavior is unchanged.

Blank automatic-text queries return no matches in the low-level engine without initializing a model, consistent with keyword search. Omitting text altogether still requests recent records. The vault and CLI continue to reject blank search text with a validation error.
