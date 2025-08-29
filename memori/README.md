# memori

**A tiny FOSS memory layer (CRUD + reflection + gap detection) you can run today.**

Status: **Scaffold only (no implementation yet).** This repo contains structure, docs, and configs to be filled in.

## What it is (20% features → 80% impact)

- **Memory CRUD** (create/read/update/delete) over simple memory records
- **Reflection** (merge duplicates, mark stale by TTL)
- **Gap detection** (`check_gaps(required_slots)`)

## Why

Most OSS apps/agents can store & recall facts. Few can reflect, detect gaps, or flag stale info. `memori` provides those minimal meta-memory primitives as a small, composable library with a demo app.

## Quickstart (will work once code lands)

```bash
git clone https://github.com/archit15singh/memori.git
cd memori
docker compose up -d                  # brings up Postgres (+ optional Redis/Valkey)
# run the demo app (after implementation)
# uv run app/ui.py  OR  python -m app.ui
```

> Note: The compose file currently uses a Redis-compatible image. Swap to Valkey if preferred.

## Repo layout

```
memori/
  src/memori/
    core/           # CRUD, reflection, gap detection (library API)
    backends/       # Postgres (pgvector), Redis/Valkey adapters
    adapters/       # LangChain/LlamaIndex wrappers (future)
  app/
    ui/             # FastAPI + HTMX demo UI (chat + memory CRUD + reflect)
    agent/          # Wiring for the demo agent
  examples/         # Notebook/CLI demos
  docs/             # Blog + diagrams
  tests/            # Unit tests (names reserved, to be implemented)
  .github/workflows # CI scaffold
  docker-compose.yml
```

## Roadmap

See [ROADMAP.md](ROADMAP.md) for versioned milestones (v0.1 core, v0.2+ enhancements).

## License

Apache-2.0. See [LICENSE](LICENSE).
