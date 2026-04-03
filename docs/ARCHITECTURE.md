# Architecture

OpenWatch uses an **open-core** model: a public MIT-licensed layer and a private BSL-licensed analytics engine.

## High-Level Diagram

```
                     ┌──────────────────────────────────┐
   Browser / CLI ───▶│  Next.js frontend  (Vercel)       │
                     │  apps/web/                         │
                     └──────────────┬───────────────────┘
                                    │ HTTP
                     ┌──────────────▼───────────────────┐
                     │  Public FastAPI gateway            │
                     │  api/  (port 8000)                 │
                     │  Rate limiting · CORS · Cache      │
                     └──────────────┬───────────────────┘
                                    │ CORE_SERVICE_URL
                                    │ (internal HTTP)
                     ┌──────────────▼───────────────────┐
                     │  openwatch-core  (private)        │
                     │  Internal API  (port 8001)        │
                     │  Typologies · ER · AI · Workers   │
                     └──────────────┬───────────────────┘
                                    │
              ┌─────────────────────▼──────────────────┐
              │  PostgreSQL (pgvector)   Redis           │
              └────────────────────────────────────────┘
```

## Public Layer (`openwatch`)

Responsible for:
- Serving the citizen-facing web portal
- Exposing the public REST API (`/public/*`)
- Handling authentication, rate limiting, and caching
- Proxying analytical queries to `openwatch-core`

Key modules:
- `api/app/routers/public.py` — public endpoint definitions
- `api/app/adapters/core_adapter.py` — delegation to core service
- `api/core_client.py` — HTTP client for core service
- `shared/config.py` — unified settings (`CORE_SERVICE_URL`, `CORE_API_KEY`)

## Private Layer (`openwatch-core`)

Responsible for:
- Ingesting government data (Celery workers)
- Running 28 corruption-risk typologies
- Entity resolution (CNPJ/CPF deduplication, graph clustering)
- AI-powered signal explanation and classification
- Exposing `/internal/*` endpoints to the public gateway

## Communication Protocol

The public API calls `openwatch-core` over an internal HTTP channel authenticated with `CORE_API_KEY`. All endpoints are under `/internal/`. The public layer never queries the database directly in split mode.

## Database

PostgreSQL 17 with `pgvector` for embedding storage and `pg_trgm` for entity search. Schema migrations are managed by Alembic in `openwatch-core`.

## Deployment Targets

| Environment | API | Frontend | Workers |
|-------------|-----|----------|---------|
| Local dev | `uv run uvicorn` | `npm run dev` | openwatch-core |
| Docker (full) | Docker Compose | Docker Compose | openwatch-core compose |
| Production | AWS ECS Fargate | Vercel | AWS ECS Fargate (core) |
