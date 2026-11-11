---
id: identity
type: procedure
tags: [lorevell, maintainer]
---

# Stable note IDs survive file renames

Every active note needs YAML frontmatter with a unique safe string id. IDs accept letters, digits, hyphens and underscores. Preserve the stable id when renaming a file; the filename is not the durable identity. Duplicate IDs are invalid. Exact IDs take precedence over prefix matches.

Source: https://github.com/archit15singh/lorevell/blob/9dd899af947b9261f0de7058fecbdd421bd769ff/lorevell-core/src/vault.rs

## Related
- [[links]]
