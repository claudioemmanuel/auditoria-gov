.PHONY: env up down restart build dev dev-lite dev-down dev-lite-down web logs test test-cov lint typecheck boundaries migrate migrate-new seed clean sync install

env:
	node scripts/detect-resources.js

up:
	npm run docker:up

down:
	npm run docker:down

restart:
	make down && make up

DC      = docker compose
DC_LITE = docker compose -f docker-compose.yml -f docker-compose.dev-lite.yml

# ── Docker build ──────────────────────────────────────────────────────────────
build:
	$(DC) build

# ── Development ───────────────────────────────────────────────────────────────
# Requires openwatch-core to be running first (it owns postgres, redis, core-api).
# Start core:   cd ../openwatch-core && make dev-lite
# Then:         make dev-lite   (this repo)
dev:
	$(DC) up -d
	@echo ""
	@echo "  Public services running (full mode):"
	@echo "    API:  http://localhost:8000"
	@echo "    Web:  http://localhost:3000 (containerised)"
	@echo ""

dev-lite:
	$(DC_LITE) up -d api
	@echo ""
	@echo "  Public services running (lite mode — web is native):"
	@echo "    API:  http://localhost:8000"
	@echo ""
	@echo "  Start the frontend natively:"
	@echo "    make web"
	@echo ""

web:
	cd apps/web && NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev

dev-down:
	$(DC) down

dev-lite-down:
	$(DC_LITE) down

logs:
	docker compose logs -f --tail=100

# ── Database ──────────────────────────────────────────────────────────────────
migrate:
docker compose run --rm api alembic -c /app/api/alembic.ini upgrade head

migrate-new:
docker compose run --rm api alembic -c /app/api/alembic.ini revision --autogenerate -m "$(name)"

seed:
docker compose run --rm api python -c "from shared.config import settings; print('DB:', settings.DATABASE_URL)"

# ── Tests ─────────────────────────────────────────────────────────────────────
test:
uv run pytest tests/public -q

test-cov:
uv run pytest tests/public --cov --cov-report=html -q

# ── Quality ───────────────────────────────────────────────────────────────────
lint:
docker compose run --rm api ruff check packages/ api/ shared/
cd apps/web && npm run lint

typecheck:
docker compose run --rm api mypy packages/ api/ shared/ --ignore-missing-imports
cd apps/web && npm run typecheck

boundaries:
docker compose run --rm api lint-imports --config .import-linter

# ── IDE tooling (optional — for editor/LSP support only) ─────────────────────
install: sync

sync:
	uv sync --all-packages
	pnpm install

# ── Cleanup ───────────────────────────────────────────────────────────────────
clean:
docker compose down -v
find . -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null; true
find . -name '.pytest_cache' -type d -exec rm -rf {} + 2>/dev/null; true
