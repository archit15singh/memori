---
id: dream-git
type: procedure
tags: [lorevell, maintainer]
---

# Use a dedicated Git root for consolidation

Dream requires a dedicated Git repository whose top-level directory is the vault. Pending knowledge edits are snapshotted in a baseline commit before invoking one existing headless agent. Resolve non-knowledge changes first. Ordinary file edits do not require Git; consolidation uses Git for validation and rollback.

Source: https://github.com/archit15singh/lorevell/blob/9dd899af947b9261f0de7058fecbdd421bd769ff/lorevell-python/python/lorevell_cli/dream.py

## Related
- [[rollback]]
