---
id: links
type: procedure
tags: [lorevell, maintainer]
---

# Resolve explicit wiki links without guessing

Wiki links resolve by exact stable ID first, then exact vault-relative filename, then unique basename. Ambiguous basenames and missing targets remain unresolved diagnostics. Anchor and display alias portions are stripped for target resolution. Wiki syntax inside ordinary fenced or inline code does not create a relationship.

Source: https://github.com/archit15singh/lorevell/blob/9dd899af947b9261f0de7058fecbdd421bd769ff/lorevell-core/src/vault.rs

## Related
- [[identity]]
