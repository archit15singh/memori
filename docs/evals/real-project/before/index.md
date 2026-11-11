---
id: index
type: procedure
tags: [lorevell, maintainer]
---

# Rebuild the search index after file edits

Run lorevell index after native Markdown edits. Indexing validates the complete active source set before transactionally updating cached rows, source hashes and explicit links. Invalid notes fail before cache mutation, avoiding a partially updated index. Unchanged source hashes retain cached vectors.

Source: https://github.com/archit15singh/lorevell/blob/9dd899af947b9261f0de7058fecbdd421bd769ff/lorevell-core/src/vault.rs

## Related
- [[markdown]]
