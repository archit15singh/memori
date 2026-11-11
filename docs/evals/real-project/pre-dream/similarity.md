---
id: similarity
type: procedure
tags: [lorevell, maintainer]
---

# Interpret the semantic similarity gate correctly

The raw cosine min_similarity gate applies before age/use adjustment. In hybrid search, a literal keyword match can still be returned below that semantic floor. A similarity threshold is not a universal final relevance filter. Supplied threshold and query vectors must satisfy validation.

Source: https://github.com/archit15singh/lorevell/blob/9dd899af947b9261f0de7058fecbdd421bd769ff/docs/relevance.md

## Related
- [[hybrid]]
