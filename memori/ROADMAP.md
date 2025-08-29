# Roadmap

## v0.1.0 — Core (20% features → 80% impact)
- Memory CRUD over Postgres
- Minimal reflection (`reflect()` merges duplicates, marks stale by TTL)
- Gap detection (`check_gaps(required_slots)`)
- FastAPI+HTMX demo UI (chat, memory table, Reflect button)
- Docker Compose (Postgres; optional Redis/Valkey)
- 4 unit tests: gaps, staleness, reflect-merge, confidence update
- README with 2 GIFs

## v0.2.x — Provenance & Policies (Low-effort, high clarity)
- Provenance fields & basic versioning
- Simple forgetting policy (pin + age-based prune)
- Conflict resolution UI

## v0.3.x — Integrations
- LangChain & LlamaIndex adapters
- Qdrant backend (vector-native) — alt to pgvector

## v0.4.x — UX & Ops
- Timeline view of memory changes
- Search/filter/tags in UI
- Basic RBAC; export/import

## v0.5.x — Background Reflection & Multi-agent
- Scheduled reflection jobs
- Shared vs private memory spaces
