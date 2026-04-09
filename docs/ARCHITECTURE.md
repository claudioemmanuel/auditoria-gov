
# Architecture — OpenWatch (Public Layer)

OpenWatch uses an **open-core** model: a public MIT-licensed layer and a private BSL-licensed analytics engine.

---

## High-Level Overview

```
┌──────────────────────────────────────────────────────────────┐
│  openwatch  (public, MIT)                        │
│  ┌───────────────┐   ┌────────────────────────────┐ │
│  │  Next.js    │   │  FastAPI public gateway   │ │
│  │  (Vercel)   │──▶│  api/                     │ │
│  └───────────────┘   └───────────────┬────────────┘ │
└──────────────────────────────┬───────────────┘
                               │ CORE_SERVICE_URL   │
                               ▼                    │
┌───────────────────────────────────────────────────┐
│  openwatch-core  (private, BSL 1.1)              │
│  Analytics · ER · Typologies · Workers · Infra   │
└───────────────────────────────────────────────────┘
```

---

## Public Layer (`openwatch`)

**Responsibilities:**
- Serve the citizen-facing web portal (Next.js)
- Expose the public REST API (`/public/*`)
- Handle authentication, rate limiting, and caching
- Proxy analytical queries to `openwatch-core`

**Key modules:**
- `api/app/routers/public.py` — public endpoint definitions
- `api/app/adapters/core_adapter.py` — delegation to core service
- `api/core_client.py` — HTTP client for core service
- `shared/config.py` — unified settings (`CORE_SERVICE_URL`, `CORE_API_KEY`)

---

## Private Layer (`openwatch-core`)

**Responsibilities:**
- Ingest government data (Celery workers)
- Run 28 corruption-risk typologies
- Entity resolution (CNPJ/CPF deduplication, graph clustering)
- AI-powered signal explanation and classification
- Expose `/internal/*` endpoints to the public gateway

---

## Communication Protocol

The public API calls `openwatch-core` over an internal HTTP channel authenticated with `CORE_API_KEY`. All endpoints are under `/internal/`. The public layer never queries the database directly in split mode.

---

## Database

PostgreSQL 17 with `pgvector` for embedding storage and `pg_trgm` for entity search.

### Schema ownership

Schema migrations are managed by Alembic **exclusively in `openwatch-core`**. The public repo has no `alembic/` directory and no ORM models of its own; `openwatch_models.base.Base` is a shared declarative base used by openwatch-core's ORM classes and re-exported through the workspace package so both repos can reference the same metadata tree.

To run migrations:

```bash
cd openwatch-core
docker compose exec core-api sh -c 'cd /app/apps && uv run alembic -c api/alembic.ini upgrade head'
```

---

## Deployment Targets

| Environment   | API              | Frontend      | Workers                |
|---------------|------------------|---------------|------------------------|
| Local dev     | `uv run uvicorn` | `npm run dev` | openwatch-core         |
| Docker (full) | Docker Compose   | Docker Compose| openwatch-core compose |
| Production    | AWS ECS Fargate  | Vercel        | AWS ECS Fargate (core) |
