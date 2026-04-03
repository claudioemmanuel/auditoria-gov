# CLAUDE.md

Guidance for AI coding assistants working on OpenWatch.

## Project Snapshot

OpenWatch is a deterministic citizen-auditing platform for Brazilian federal public data.
The project uses an open-core model:

- `openwatch-br/openwatch` (this repo, MIT): public OSS layer
- `openwatch-br/openwatch-core` (private, BSL 1.1): typologies, analytics, pipelines

## Canonical Structure

| What | Canonical path |
|------|---------------|
| FastAPI backend | `apps/api/` |
| Next.js frontend | `apps/web/` |
| Celery worker | `core/pipelines/` |
| Config | `packages/config/openwatch_config/settings.py` |
| Logging | `packages/utils/openwatch_utils/logging.py` |
| DB session | `packages/db/openwatch_db/db.py` |
| Public models | `packages/models/openwatch_models/` |

> Legacy `shared/`, `api/`, `worker/` directories exist for backward compatibility
> during the split transition. Do not add new code there.

## Key Commands

```bash
# Backend tests (public layer)
uv run pytest tests/public -q

# Backend tests (core — requires CORE_CI_ENABLED secret)
uv run pytest tests/core -q

# Lint
uv run ruff check packages/ apps/api/

# Boundary check
uv run python tools/check_boundaries.py

# Frontend
cd apps/web && npm ci && npm run lint && npm run build

# Local dev stack
make dev                    # Postgres + Redis in Docker
make migrate                # Run alembic migrations
```

## Common Change Paths

| What | Where |
|------|-------|
| New public connector | `packages/connectors/openwatch_connectors/` + tests |
| New public model | `packages/models/openwatch_models/` |
| Public API endpoint | `apps/api/app/routers/public.py` |
| DB migration | `apps/api/alembic/versions/` — no `CONCURRENTLY` inside functions |
| UI component | `apps/web/src/components/` |
| SDK method | `packages/sdk/src/index.ts` |

## Rules

- Coding conventions: `.claude/rules/coding.md`
- Testing conventions: `.claude/rules/testing.md`
- Code review checklist: `.claude/skills/review/SKILL.md`

## Configuration

- `CORE_SERVICE_URL` — if set, the API uses CoreClient (HTTP to openwatch-core)
- `CORE_API_KEY` — required when `CORE_SERVICE_URL` is set
- `CPF_HASH_SALT` — HMAC salt for CPF hashing; never change in production
- `INTERNAL_API_KEY` — authenticates internal API endpoints

## Git Workflow

All work follows: `main` → branch (`feat/fix/docs/chore/...`) → PR → review → merge.
Never commit directly to `main`. Branch name and PR title must follow conventional commits.
Never include Co-authored-by or AI attribution in commits.
