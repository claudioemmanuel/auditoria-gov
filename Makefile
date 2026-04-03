.PHONY: build dev dev-down logs test test-cov lint typecheck boundaries migrate migrate-new seed clean sync

# Docker build
build:
docker compose build

# Full stack in Docker (public layer only — workers run from openwatch-core)
dev:
docker compose up -d

dev-down:
docker compose down

logs:
docker compose logs -f --tail=100

# Database
migrate:
docker compose run --rm api alembic -c /app/api/alembic.ini upgrade head

migrate-new:
docker compose run --rm api alembic -c /app/api/alembic.ini revision --autogenerate -m "$(name)"

seed:
docker compose run --rm api python -c "from shared.config import settings; print('DB:', settings.DATABASE_URL)"

# Tests
test:
docker compose run --rm api pytest tests/public -q

test-cov:
docker compose run --rm api pytest tests/public --cov --cov-report=html -q

# Quality
lint:
docker compose run --rm api ruff check packages/ api/ shared/
cd apps/web && npm run lint

typecheck:
docker compose run --rm api mypy packages/ api/ shared/ --ignore-missing-imports
cd apps/web && npm run typecheck

boundaries:
docker compose run --rm api lint-imports --config .import-linter

# Optional: local install for IDE/editor support only
sync:
uv sync --all-packages
pnpm install

# Cleanup
clean:
docker compose down -v
find . -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null; true
find . -name '.pytest_cache' -type d -exec rm -rf {} + 2>/dev/null; true
