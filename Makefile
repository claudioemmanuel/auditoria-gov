.PHONY: dev dev-down web logs test test-cov lint typecheck boundaries sync install clean

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
# Schema ownership belongs to openwatch-core. There are intentionally no
# migrate / migrate-new targets here. To run migrations:
#   cd ../openwatch-core && make migrate

# ── Tests ─────────────────────────────────────────────────────────────────────
test:
	uv run pytest tests/public -q

test-cov:
	uv run pytest tests/public --cov --cov-report=html -q

# ── Quality ───────────────────────────────────────────────────────────────────
lint:
	docker compose run --rm api ruff check packages/ api/
	cd apps/web && npm run lint

typecheck:
	docker compose run --rm api mypy packages/ api/ --ignore-missing-imports
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
