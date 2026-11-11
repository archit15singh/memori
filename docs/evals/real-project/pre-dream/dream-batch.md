---
id: dream-batch
type: procedure
tags: [lorevell, maintainer]
---

# Acknowledge only successful consolidation batches

Dream compares current file hashes to .lorevell/dream-state.json from the last successful run. --max-notes bounds selected changed candidates and touched knowledge files. Other candidates stay pending. Archived paths are excluded from candidate selection. A second run without changes returns unchanged without launching an agent.

Source: https://github.com/archit15singh/lorevell/blob/9dd899af947b9261f0de7058fecbdd421bd769ff/lorevell-python/python/lorevell_cli/dream.py

## Related
- [[dream-failure]]
