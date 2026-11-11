---
id: rollback
type: procedure
tags: [lorevell, maintainer]
---

# Undo a consolidation with Git and then reindex

Run git -C <vault> revert <consolidation-commit> to undo a successful consolidation. Then run lorevell --vault <vault> index to make search reflect the restored Markdown files. Git history preserves the baseline and consolidation; a disposable index alone is not the rollback mechanism.

Source: https://github.com/archit15singh/lorevell/blob/9dd899af947b9261f0de7058fecbdd421bd769ff/README.md

## Related
- [[dream-git]]
