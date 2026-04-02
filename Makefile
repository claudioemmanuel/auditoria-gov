.PHONY: install dev dev-full dev-down logs test test-core test-all test-cov lint typecheck boundaries migrate migrate-new seed ingest pipeline clean

# ── Setup ─────────────────────────────────────────────────────────────────────
install:
	uv sync --all-extras
	pnpm install

# ── Development modes ─────────────────────────────────────────────────────────
# Lightweight: only Postgres + Redis via Docker; run api/web natively
dev:
	docker compose -f infra/docker/docker-compose.yml -f infra/docker/docker-compose.dev-lite.yml up -d
	@echo ""
	@echo "  Services running:"
	@echo "    Postgres:  localhost:5432"
	@echo "    Redis:     localhost:6379"
	@echo ""
	@echo "  Start API:  cd apps/api && uv run uvicorn app.main:app --reload --port 8000"
	@echo "  Start Web:  cd apps/web && NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev"
	@echo ""

# Full stack: all services in Docker (~7.5 GB RAM)
dev-full:
	docker compose -f infra/docker/docker-compose.yml up -d

dev-down:
	docker compose -f infra/docker/docker-compose.yml down

logs:
	docker compose -f infra/docker/docker-compose.yml logs -f --tail=100

# ── Database ──────────────────────────────────────────────────────────────────
migrate:
	cd apps/api && uv run alembic upgrade head

migrate-new:
	cd apps/api && uv run alembic revision --autogenerate -m "$(name)"

seed:
	bash infra/scripts/seed.sh

# ── Tests ─────────────────────────────────────────────────────────────────────
test:
	uv run pytest tests/public -q

test-core:
	uv run pytest tests/core -q

test-all:
	uv run pytest -q

test-cov:
	uv run pytest --cov --cov-report=html -q

# ── Quality ───────────────────────────────────────────────────────────────────
lint:
	uv run ruff check packages/ core/ apps/api/
	cd apps/web && npm run lint

typecheck:
	uv run mypy packages/ core/ apps/api/ --ignore-missing-imports
	cd apps/web && npm run typecheck 2>/dev/null || true

boundaries:
	uv run lint-imports --config .import-linter

# ── Pipeline utils ────────────────────────────────────────────────────────────
ingest:
	curl -s -X POST http://localhost:8000/internal/ingest/all \
	  -H "X-Internal-Api-Key: $$(cat .env | grep INTERNAL_API_KEY | cut -d= -f2)"

pipeline:
	curl -s -X POST http://localhost:8000/internal/pipeline/full \
	  -H "X-Internal-Api-Key: $$(cat .env | grep INTERNAL_API_KEY | cut -d= -f2)"

# ── Cleanup ───────────────────────────────────────────────────────────────────
clean:
	docker compose -f infra/docker/docker-compose.yml down -v
	find . -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null; true
	find . -name '.pytest_cache' -type d -exec rm -rf {} + 2>/dev/null; true

