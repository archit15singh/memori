# Project Structure

## Repository Organization

```
memori/
├── .kiro/                    # Kiro IDE configuration and steering
├── .vscode/                  # VS Code settings
├── core/                     # Core memory engine (planned)
│   ├── embed.py             # Embedding generation
│   ├── memory.py            # Memory CRUD operations
│   └── reflect.py           # Reflection jobs
├── api/                      # FastAPI application (planned)
│   ├── endpoints/           # API route handlers
│   ├── models/              # Pydantic data models
│   └── middleware/          # Auth, CORS, etc.
├── workers/                  # Background job processors (planned)
├── migrations/               # Database schema migrations (planned)
├── tests/                    # Test suite (planned)
├── docker-compose.yml        # Local development stack (planned)
├── Dockerfile               # Container definition (planned)
├── pyproject.toml           # Python project configuration (planned)
└── README.md                # Project documentation
```

## Key Files

- **README.md**: Comprehensive project documentation with quickstart guide
- **spec.md**: Technical specification and implementation roadmap
- **pycon-2025.md**: Demo project context and philosophy
- **letter-to-dev.md**: Developer onboarding guide with API usage patterns

## Development Conventions

- **API Structure**: RESTful endpoints following `/api/v1/` pattern
- **Database Models**: SQLAlchemy ORM with Alembic migrations
- **Background Jobs**: Separate worker processes for reflection tasks
- **Configuration**: Environment-based config with `.env` files
- **Documentation**: Inline docstrings + automatic OpenAPI generation

## Data Flow Architecture

1. **Ingestion**: `POST /ingest` → Postgres episodic_log → pgvector semantic_index
2. **Retrieval**: `GET /remember` → semantic search + KG traversal
3. **Reflection**: `GET /reflect` → background jobs → memory updates
4. **Policy**: `POST /policy/delete` → soft delete + provenance tracking

## Testing Strategy

- Unit tests for core memory operations
- Integration tests for API endpoints
- End-to-end tests for reflection workflows
- Performance benchmarks for retrieval latency

## Deployment Considerations

- Docker containers for consistent environments
- Postgres + Redis as external services
- Horizontal scaling via stateless API design
- Background workers can scale independently