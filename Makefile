.PHONY: dev dev-down web logs migrate migrate-new seed test test-cov lint typecheck boundaries sync install clean

# ── Development ───────────────────────────────────────────────────────────────
# Requires openwatch-core to be running first (it owns postgres, redis, core-api).
# Start core first:  cd ../openwatch-core && make dev
# Then:              make dev (this repo)
dev:
	docker compose up -d --build
	@echo ""
	@echo "  Public services running:"
	@echo "    API:  http://localhost:8000"
	@echo ""
	@echo "  Start frontend natively: make web"
	@echo ""

dev-down:
	docker compose down

web:
	cd apps/web && NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev

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

# ── IDE tooling (editor / LSP support) ───────────────────────────────────────
install: sync

sync:
	uv sync --all-packages
	pnpm install

# ── Cleanup ───────────────────────────────────────────────────────────────────
clean:
	docker compose down -v
	find . -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null; true
	find . -name '.pytest_cache' -type d -exec rm -rf {} + 2>/dev/null; true
