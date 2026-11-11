---
id: dream-failure
type: procedure
tags: [lorevell, maintainer]
---

# Failed consolidation retains edits and leaves progress pending

On timeout or agent failure, dream retains inspectable edits and does not acknowledge the batch checkpoint. Child output is local in .lorevell/dream-last.log. Timeout handling terminates the process group on POSIX, escalating to kill if needed. Inspect and repair before retrying.

Source: https://github.com/archit15singh/lorevell/blob/9dd899af947b9261f0de7058fecbdd421bd769ff/lorevell-python/python/lorevell_cli/dream.py

## Related
- [[dream-batch]]
