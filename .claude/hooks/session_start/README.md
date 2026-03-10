# Hook: session_start

## Purpose

Commands and context to load at the start of every Claude Code session on this project.

## Recommended Session Start Checklist

```bash
# 1. Check stack health
docker compose ps

# 2. Confirm .env is present (never commit it)
ls -la .env

# 3. Check for pending migrations
docker compose run --rm api alembic -c api/alembic.ini current

# 4. Confirm tests are green before starting work
uv run --extra test pytest -q --tb=short
```

## Context Files to Load

When starting a session on a specific area, read these files first:

| Area | Files |
|------|-------|
| New typology | `shared/typologies/registry.py`, `docs/ARCHITECTURE.md`, `.claude/rules/coding.md` |
| New connector | `shared/connectors/base.py`, `shared/connectors/veracity.py`, `docs/GOVERNANCE.md` |
| API changes | `api/app/routers/public.py`, `shared/repo/queries.py` |
| Signal pipeline | `shared/scheduler/schedule.py`, `worker/tasks/signal_tasks.py` |
| Frontend | `web/src/app/`, `web/src/components/` |

## Configuring as a Hook

To automate session start checks, add a shell script at `.claude/hooks/session_start/run.sh`:

```bash
#!/bin/bash
set -e
echo "=== AuditorIA Session Start ==="
docker compose ps 2>/dev/null || echo "Docker stack not running"
[ -f .env ] && echo ".env present ✓" || echo "WARNING: .env missing"
echo "==============================="
```

Then configure it in `.claude/settings.json` under `hooks.session_start`.
