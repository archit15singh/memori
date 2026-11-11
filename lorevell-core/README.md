# lorevell-core 2.0

Rust implementation of a Markdown-first knowledge vault and its rebuildable SQLite retrieval index.

```rust,no_run
use lorevell_core::{Vault, SearchQuery};
use std::path::Path;

let vault = Vault::open(Path::new("memory"))?;
vault.add("# Procedure\nUse transactions for atomic multi-statement writes.",
          serde_json::json!({"type":"procedure", "tags":["sqlite"]}))?;
vault.index(true)?;
let results = vault.search(SearchQuery {
    text: Some("atomic database writes".into()),
    ..Default::default()
}, 3)?;
# Ok::<(), lorevell_core::LorevellError>(())
```

`Vault` owns Markdown parsing, atomic writes, archives, source hashes and explicit wiki links/backlinks. Indexing validates the source set before changing cached rows. Graph expansion is one hop with an overall extra-note limit. Use `index(false)` plus `SearchQuery { text_only: true, .. }` for literal-only operation.

The existing `Lorevell` SQLite engine remains available for low-level consumers. It provides FTS5, cosine vectors, RRF hybrid ranking, metadata filters and detailed database clocks. It is retrieval plumbing for a vault, not a second authoritative store for the same knowledge. Native vectors are f32 BLOBs; default model embeddings have 384 dimensions. Disable the default `embeddings` feature for a no-model build.

See the [repository README](https://github.com/archit15singh/lorevell), `docs/v2.md`, and the Rust integration tests for the complete product contract. MIT licensed.
