# CLAUDE.md

Guidance for Claude Code contributors working on AuditorIA Gov.

## Project Snapshot

AuditorIA Gov is a deterministic citizen-auditing platform for Brazilian federal public data.

- Backend API: `api/` (FastAPI)
- Async jobs: `worker/` (Celery + Beat)
- Shared domain/core: `shared/`
- Frontend: `web/` (Next.js)
- Tests: `tests/`

Core principle: risk signals are reproducible and evidence-based; the optional LLM layer is explanatory only.

## Key Commands

Backend setup and tests:

```bash
uv sync --extra test
uv run --extra test pytest -q
```

Frontend setup and checks:

```bash
cd web
npm ci
npm run lint
npm run build
```

Run local stack:

```bash
docker compose up --build
```

Run DB migrations:

```bash
docker compose run --rm api alembic -c api/alembic.ini upgrade head
```

## Common Change Paths

- New connector: `shared/connectors/` + `shared/connectors/__init__.py` + tests in `tests/connectors/`
- New typology: `shared/typologies/` + `shared/typologies/registry.py` + tests in `tests/typologies/`
- Public API responses: `api/app/routers/public.py` + repository queries in `shared/repo/queries.py`
- Scheduled pipelines: `shared/scheduler/schedule.py` and `worker/tasks/`
- UI pages/components: `web/src/app/` and `web/src/components/`

## Guardrails

- Do not commit secrets, tokens, `.env`, or bulk datasets.
- Preserve LGPD behavior (for example CPF hashing, no raw CPF persistence).
- Keep typology logic deterministic and auditable.
- Add or update tests for all behavioral changes.
- Prefer small, reviewable PRs with explicit verification output.
- All outbound HTTP must pass through `shared/connectors/domain_guard.py` whitelist. Non-government domains require a `DomainException` with justification and review date.
- New data sources require a `SourceVeracityProfile` in `shared/connectors/veracity.py` and an update to `docs/GOVERNANCE.md`.
- LLM usage is explanatory only — never affects scoring. Functions calling LLMs must use the `@explanatory_only` decorator from `shared/ai/provider.py`.
