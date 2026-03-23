# CLAUDE.md

Guidance for Claude Code contributors working on OpenWatch.

## Project Snapshot

OpenWatch is a deterministic citizen-auditing platform for Brazilian federal public data.

- `api/` — FastAPI backend
- `worker/` — Celery + Beat async jobs
- `shared/` — domain logic, connectors, typologies
- `web/` — Next.js frontend
- `tests/` — pytest suite

**Core principle:** risk signals are reproducible and evidence-based; the LLM layer is explanatory only.

## Key Commands

```bash
# Backend tests
uv run --extra test pytest -q

# Frontend
cd web && npm ci && npm run lint && npm run build

# Local stack
docker compose up --build

# DB migrations
docker compose run --rm api alembic -c api/alembic.ini upgrade head
```

## Common Change Paths

| What | Where |
|------|-------|
| New connector | `shared/connectors/` + `__init__.py` + `tests/connectors/` |
| New typology | `shared/typologies/` + `registry.py` + `tests/typologies/` |
| Public API | `api/app/routers/public.py` + `shared/repo/queries.py` |
| Scheduled jobs | `shared/scheduler/schedule.py` + `worker/tasks/` |
| UI | `web/src/app/` + `web/src/components/` |
| DB migration | `api/alembic/versions/` — no `CONCURRENTLY` inside functions |

## Rules & Skills

- Coding conventions: `.claude/rules/coding.md`
- Testing conventions: `.claude/rules/testing.md`
- Code review checklist: `.claude/skills/review/SKILL.md`
- Safe refactor workflow: `.claude/skills/refactor/SKILL.md`
- Utility scripts: `tools/SCRIPTS.md`
- Prompt templates: `tools/PROMPTS.md`
