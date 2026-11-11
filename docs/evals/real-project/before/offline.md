---
id: offline
type: procedure
tags: [lorevell, maintainer]
---

# Use keyword search without model inference

lorevell search "topic" --text-only avoids local model inference. lorevell index --text-only builds or refreshes the index without embedding generation. This keyword-only path supports offline operation without downloading the embedding model. Hybrid search may download its local model on first use.

Source: https://github.com/archit15singh/lorevell/blob/9dd899af947b9261f0de7058fecbdd421bd769ff/README.md

## Related
- [[embeddings]]
