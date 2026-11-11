---
id: locking
type: procedure
tags: [lorevell, maintainer]
---

# Know the boundary of vault writer locks

Lorevell mutations and indexing acquire an operating-system file lock. Atomic temporary-file replacement protects individual note writes. Native editors do not acquire these locks; stop other writers during consolidation. There is no general concurrent native-edit merge guarantee or cross-filesystem/database atomic transaction.

Source: https://github.com/archit15singh/lorevell/blob/9dd899af947b9261f0de7058fecbdd421bd769ff/lorevell-core/src/vault.rs

## Related
- [[dream-validation]]
