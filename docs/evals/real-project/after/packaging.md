---
id: packaging
type: procedure
tags: [lorevell, maintainer]
---

# Verify an installed wheel in a fresh environment

Build a wheel with maturin build --release --manifest-path lorevell-python/Cargo.toml. Install the resulting wheel into a new virtual environment, then verify lorevell --version, native imports, add/search, packaged agent skills and dream dry-run. A passing editable installation alone does not establish wheel completeness.

Source: https://github.com/archit15singh/lorevell/blob/9dd899af947b9261f0de7058fecbdd421bd769ff/docs/rebrand.md

## Related
- [[skills]]
