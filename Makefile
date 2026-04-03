.PHONY: install dev dev-full dev-down logs test test-cov lint typecheck boundaries migrate migrate-new seed clean

# ── Setup ─────────────────────────────────────────────────────────────────────
install:
uv sync --all-packages
pnpm install

# ── Development ───────────────────────────────────────────────────────────────
# Lightweight: only Postgres + Redis; run api/web natively.
dev:
docker compose -f docker-compose.yml -f docker-compose.dev-lite.yml up -d postgres redis
@echo ""
@echo "  Infrastructure running:"
@echo "    Postgres: localhost:5432"
@echo "    Redis:    localhost:6379"
@echo ""
@echo "  Start API:  uv run uvicorn api.app.main:app --reload --port 8000"
@echo "  Start Web:  cd apps/web && NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev"
@echo ""

# Full stack (public layer only — workers run from openwatch-core).
dev-full:
docker compose up -d

dev-down:
docker compose down

logs:
docker compose logs -f --tail=100

# ── Database ──────────────────────────────────────────────────────────────────
migrate:
uv run alembic -c api/alembic.ini upgrade head

migrate-new:
uv run alembic -c api/alembic.ini revision --autogenerate -m "$(name)"

seed:
uv run python -c "from shared.config import settings; print('DB:', settings.DATABASE_URL)"

# ── Tests ─────────────────────────────────────────────────────────────────────
test:
uv run pytest tests/public -q

test-cov:
uv run pytest tests/public --cov --cov-report=html -q

# ── Quality ───────────────────────────────────────────────────────────────────
lint:
uv run ruff check packages/ api/ shared/
cd apps/web && npm run lint

typecheck:
uv run mypy packages/ api/ shared/ --ignore-missing-imports
cd apps/web && npm run typecheck

boundaries:
uv run lint-imports --config .import-linter

# ── Cleanup ───────────────────────────────────────────────────────────────────
clean:
docker compose down -v
find . -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null; true
find . -name '.pytest_cache' -type d -exec rm -rf {} + 2>/dev/null; true
