# Time semantics: vault and low-level engine

Lorevell 2.0 retains knowledge in Markdown. Generated notes include finite numeric epoch-second `created_at` and `updated_at` frontmatter. `update` preserves creation time and advances update time. Native file edits preserve whatever metadata the author leaves in the file; reindexing does not invent factual validation. When a timestamp is absent, the file's modification time initializes the derived engine clocks.

The current vault uses those source timestamps when populating the existing retrieval engine. Usage counters are not canonical vault knowledge, and rebuilding the cache does not preserve a history of reads. Neither popularity nor recent modification proves a note true. Consolidation flags uncertain or stale claims rather than certifying them automatically.

The retained low-level Rust `Lorevell` / Python `PyLorevell` engine has more detailed clocks for its database API:

| Clock | Engine behavior |
| --- | --- |
| `created_at` | Initial insertion |
| `updated_at` | Content, vector, metadata or explicit validation write |
| `content_updated_at` | Changed content bytes |
| `validated_at` | Explicit caller assertion of validation |
| `last_accessed` / `access_count` | `get` usage, separate from factual age |

Its existing v4 migration and regression tests remain. The decay adjustment is bounded popularity (at most 1.5×) times `exp(-0.01 * factual_age_days)`; negative cosine uses the inverse adjustment so old negative matches cannot improve through decay. Hybrid search uses the resulting ranks. These engine facilities are not exposed as a second persistent source of truth by the 2.0 CLI.
