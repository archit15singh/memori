# memori-ai-core

Persistent memory for AI coding agents — SQLite + FTS5 + vector search in a single binary.

This is the Rust engine behind the **[`py-memori`](https://pypi.org/project/py-memori/)** Python package
and the `memori` CLI. Most users want the Python package:

```bash
pip install py-memori
```

## Rust usage

```toml
# Cargo.toml
[dependencies]
memori-ai-core = { version = "0.7", features = ["embeddings"] }
```

```rust
use memori_core::{Memori, SearchQuery, SortField};

let db = Memori::open("memories.db")?;
let id = db.insert("Chose SQLite over Postgres for zero-config portability.",
                   Some(r#"{"type":"decision"}"#), true, None, None)?;
let hits = db.search(SearchQuery {
    text: Some("sqlite".into()),
    ..Default::default()
})?;
for m in hits { println!("{}", m.content); }
```

## Features

- **Single SQLite file** with WAL journaling — no external services, no config
- **Hybrid search**: FTS5 full-text + cosine vector fused with Reciprocal Rank Fusion (k=60)
- **Built-in embeddings** via `fastembed` (AllMiniLM-L6-V2, 384-dim, ~9ms/memory)
- **Cosine-similarity deduplication** (configurable threshold, default 0.92)
- **Access-weighted decay scoring** — frequently-used recent memories surface first
- **Prefix ID resolution** — 6+ char UUID prefixes in every ID-based command

## Design notes

- `vector_search()` is the sole hot path and the only place vectors are touched — designed
  as a drop-in seam for a future HNSW replacement. Adequate to ~100K vectors at 384 dims.
- FTS5 uses an external-content virtual table (no text duplication); triggers in `schema.rs`
  keep the index in sync.
- Schema migrations are tracked via `PRAGMA user_version` (v0→v3).

## License

MIT. See the [project repo](https://github.com/archit15singh/memori) for full documentation,
benchmarks, CLI reference, and design blog posts.