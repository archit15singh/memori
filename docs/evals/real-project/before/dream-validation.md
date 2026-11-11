---
id: dream-validation
type: procedure
tags: [lorevell, maintainer]
---

# Validate scope and evidence before committing dream edits

After the headless agent exits, dream rejects changes to non-knowledge files, Git staging/history, too many knowledge files, or deletion of an original whose bytes were not preserved. It validates and reindexes notes before its scoped commit. Structural validation cannot prove semantic truth or completeness.

Source: https://github.com/archit15singh/lorevell/blob/9dd899af947b9261f0de7058fecbdd421bd769ff/lorevell-python/python/lorevell_cli/dream.py

## Related
- [[archive]]
