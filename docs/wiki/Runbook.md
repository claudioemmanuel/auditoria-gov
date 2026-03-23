# Runbook

## Local Setup

```bash
git clone https://github.com/claudioemmanuel/openwatch.git
cd openwatch
cp .env.example .env
docker compose up --build
docker compose run --rm api alembic -c api/alembic.ini upgrade head
```

## Pipeline Trigger (Manual)

```bash
curl -X POST http://localhost:8000/internal/ingest/all
curl -X POST http://localhost:8000/internal/er/run
curl -X POST http://localhost:8000/internal/baselines/run
curl -X POST http://localhost:8000/internal/signals/run
curl -X POST http://localhost:8000/internal/coverage/update
```

## Verification

```bash
uv sync --extra test
uv run --extra test pytest -q
cd web && npm ci && npm run build
```

## Critical Environment Variables

- `DATABASE_URL`
- `REDIS_URL`
- `PORTAL_TRANSPARENCIA_TOKEN`
- `CPF_HASH_SALT`
- `CELERY_BROKER_URL`
- `CELERY_RESULT_BACKEND`
