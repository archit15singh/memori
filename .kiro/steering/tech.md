# Technology Stack

## Core Technologies

- **Backend**: Python 3.11+ with FastAPI for API layer
- **Database**: PostgreSQL with pgvector extension for semantic indexing
- **Cache**: Redis for short-term memory caching
- **Embeddings**: OpenAI API (configurable to other providers)
- **Background Jobs**: Celery/RQ/Arq for reflection workers

## Development Stack

- **Package Management**: UV (preferred) or pip
- **Code Quality**: Ruff for linting and formatting
- **Testing**: pytest for unit and integration tests
- **Containerization**: Docker + Docker Compose for local development

## Architecture Patterns

- **API-First Design**: FastAPI with automatic OpenAPI documentation
- **Microservices Ready**: Composable API that can integrate with any agent framework
- **Event-Driven**: Background reflection jobs triggered by memory changes
- **CRUD Operations**: Full memory lifecycle management (Create, Read, Update, Delete)

## Common Commands

```bash
# Development setup
docker compose up --build

# Code quality checks
make check  # runs lint + tests

# API documentation
# Available at http://localhost:8000/docs when running

# Environment configuration
cp .env.example .env
# Edit .env with your API keys and database settings
```

## Configuration

- Environment variables in `.env` file
- Database migrations handled automatically
- Redis and Postgres configured via Docker Compose
- LLM provider configurable (OpenAI, Anthropic, etc.)

## Performance Considerations

- Vector similarity search optimized with pgvector indexes
- Redis caching for frequently accessed memories
- Background job queues for non-blocking reflection operations
- Append-only episodic log for audit trail preservation