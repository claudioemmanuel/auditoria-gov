# AuditorIA Gov

Public portal for citizen auditing of Brazilian federal government data. Ingests public federal data (Executive + Legislative), performs entity resolution, generates risk signals for corruption/fraud indicators, and explains findings with reproducible evidence.

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Next.js   │────▶│   FastAPI    │────▶│ PostgreSQL  │
│   (web/)    │     │   (api/)     │     │ + pgvector  │
└─────────────┘     └──────┬──────┘     └─────────────┘
                           │                    ▲
                    ┌──────▼──────┐              │
                    │   Celery    │──────────────┘
                    │ (worker/)   │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │    Redis    │
                    └─────────────┘
```

- **shared/** — Config, models, connectors, pipeline engine (used by api + worker)
- **api/** — FastAPI public endpoints + Alembic migrations
- **worker/** — Celery tasks + Beat scheduler
- **web/** — Next.js frontend portal (PT-BR)

## Quick Start

```bash
cp .env.example .env
docker compose up --build
```

Services:
- **API:** http://localhost:8000 (Swagger at /docs)
- **Frontend:** http://localhost:3000
- **PostgreSQL:** localhost:5432
- **Redis:** localhost:6379

## Migrations

```bash
docker compose run api alembic -c api/alembic.ini upgrade head
```

## Stack

| Layer | Technology |
|-------|-----------|
| Database | PostgreSQL 17 + pgvector |
| Cache/Broker | Redis 7 |
| API | FastAPI + Uvicorn |
| Worker | Celery + Beat |
| Frontend | Next.js 15 + React 19 + Tailwind v4 + shadcn/ui |
| ORM | SQLAlchemy 2 (async) |
| LLM | OpenAI (optional, deterministic fallback) |
