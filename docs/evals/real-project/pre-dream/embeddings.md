---
id: embeddings
type: procedure
tags: [lorevell, maintainer]
---

# Local embedding model and vector format

The default local embedding model is AllMiniLM-L6-V2 with 384 dimensions. Initialization is lazy and shared. Model files may download on first inference. Native vectors are stored as f32 BLOBs; explicitly supplied vectors bypass automatic embedding generation in the low-level engine.

Source: https://github.com/archit15singh/lorevell/blob/9dd899af947b9261f0de7058fecbdd421bd769ff/lorevell-core/src/embed.rs

## Related
- [[offline]]
