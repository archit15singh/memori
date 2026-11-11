---
id: skills
type: procedure
tags: [lorevell, maintainer]
---

# Install one shared learning skill for either agent

lorevell setup --agent codex --project <directory> installs project-local skills below .agents/skills/. --agent claude installs below .claude/skills/. Both use the same packaged learning and dream instructions. Conflicting installed files require explicit --force; setup does not silently overwrite customized skills.

Source: https://github.com/archit15singh/lorevell/blob/9dd899af947b9261f0de7058fecbdd421bd769ff/lorevell-python/python/lorevell_cli/__init__.py

## Related
- [[learning]]
