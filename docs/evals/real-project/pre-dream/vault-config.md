---
id: vault-config
type: procedure
tags: [lorevell, maintainer]
---

# Select the intended vault explicitly

lorevell --vault <directory> overrides LOREVELL_VAULT. Without either, the default vault is ./memory. lorevell init creates a vault and ignores .lorevell/ and .fastembed_cache/. init initializes a dedicated Git repository unless --no-git is requested, and does not change Git identity.

Source: https://github.com/archit15singh/lorevell/blob/9dd899af947b9261f0de7058fecbdd421bd769ff/lorevell-python/python/lorevell_cli/__init__.py

## Related
- [[dream-git]]
