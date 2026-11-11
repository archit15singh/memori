---
id: fts
type: procedure
tags: [lorevell, maintainer]
---

# Literal search uses SQLite FTS5

Keyword retrieval uses SQLite FTS5 with metadata-aware indexed content. Text queries are escaped for FTS matching instead of treated as raw operators. Literal search is a different retrieval path from semantic vector similarity. Use --text-only when a local keyword-only workflow is wanted.

Source: https://github.com/archit15singh/lorevell/blob/9dd899af947b9261f0de7058fecbdd421bd769ff/lorevell-core/src/search.rs

## Related
- [[offline]]
