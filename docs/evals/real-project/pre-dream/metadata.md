---
id: metadata
type: procedure
tags: [lorevell, maintainer]
---

# Keep note metadata simple and validate its shape

Notes have YAML frontmatter with id and optional type and tags. Lorevell validates metadata rather than requiring a separate graph schema. Commands such as lorevell add --type procedure --tag sqlite create short reusable procedures. Commands can live in Markdown code blocks with their preconditions and verification.

Source: https://github.com/archit15singh/lorevell/blob/9dd899af947b9261f0de7058fecbdd421bd769ff/lorevell-core/src/vault.rs

## Related
- [[identity]]
