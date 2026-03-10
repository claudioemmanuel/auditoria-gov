# Scripts Catalog

Utility commands and shortcuts for AuditorIA Gov development.

## Development Stack

```bash
# Start full local stack
docker compose up --build

# Start in background
docker compose up -d

# Stop stack
docker compose down

# View logs for a specific service
docker compose logs -f worker-cpu
docker compose logs -f api
```

## Database

```bash
# Run migrations (head)
docker compose run --rm api alembic -c api/alembic.ini upgrade head

# Check current migration
docker compose run --rm api alembic -c api/alembic.ini current

# Create a new migration
docker compose run --rm api alembic -c api/alembic.ini revision --autogenerate -m "describe_change"

# Downgrade one step
docker compose run --rm api alembic -c api/alembic.ini downgrade -1
```

## Backend Tests

```bash
# Full suite (fast)
uv run --extra test pytest -q

# With coverage
uv run --extra test pytest --cov=shared --cov-report=term-missing

# Single typology
uv run --extra test pytest tests/typologies/test_t03.py -v

# Single connector
uv run --extra test pytest tests/connectors/test_pncp.py -v

# Watch mode (requires pytest-watch)
uv run --extra test ptw -- -q
```

## Frontend

```bash
cd web

# Install dependencies
npm ci

# Development server
npm run dev

# Type check + lint
npm run lint

# Build
npm run build
```

## Worker Tasks (Manual Trigger)

```bash
# Run PNCP ingest
docker compose run --rm worker-ingest celery -A worker.worker_app call worker.tasks.ingest_tasks.run_ingest --args='["pncp"]'

# Run entity resolution
docker compose run --rm worker-cpu celery -A worker.worker_app call worker.tasks.er_tasks.run_entity_resolution

# Run signals for a typology
docker compose run --rm worker-cpu celery -A worker.worker_app call worker.tasks.signal_tasks.run_typology --args='["T03"]'

# Load reference data
docker compose run --rm worker-ingest celery -A worker.worker_app call worker.tasks.reference_tasks.load_reference_data
```

## Code Quality

```bash
# Lint Python (ruff)
uv run ruff check shared/ api/ worker/

# Format Python
uv run ruff format shared/ api/ worker/

# Type check (if pyright installed)
uv run pyright shared/
```
