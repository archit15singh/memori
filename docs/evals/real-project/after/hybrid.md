---
id: hybrid
type: procedure
tags: [lorevell, maintainer]
---

# Fuse keyword and vector rankings with RRF

Hybrid retrieval combines keyword FTS5 and semantic cosine-vector candidates with Reciprocal Rank Fusion (RRF). Each leg uses up to three times the requested limit. Returned ranking scores are not probabilities. The existing Rust engine supplies retrieval; no LLM reranker is needed.

Source: https://github.com/archit15singh/lorevell/blob/9dd899af947b9261f0de7058fecbdd421bd769ff/lorevell-core/src/search.rs

## Related
- [[fts]]
