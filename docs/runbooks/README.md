# Operational Runbooks

This directory contains step-by-step runbooks for common operational tasks and incident response.

## Available Runbooks

| Runbook | Description | Status |
|---------|-------------|--------|
| `cold-start.md` | Full pipeline cold start from empty DB | Planned |
| `signal-rollback.md` | Emergency rollback of a faulty typology's signals | Planned |
| `submodule-update.md` | Update auditoria-gov submodule in parent repo | Planned |
| `migration-rollback.md` | Rolling back an Alembic migration in production | Planned |
| `connector-disable.md` | Disabling a broken data source connector | Planned |

## Runbook Template

```markdown
# Runbook: [Title]

**Severity:** P1 | P2 | P3
**Estimated time:** X minutes
**Requires:** [access level, tools]

## Trigger
When to use this runbook.

## Steps

1. **Step name**
   ```bash
   command here
   ```
   Expected output: `...`

2. **Step name**
   ...

## Verification
How to confirm the runbook succeeded.

## Rollback
If something went wrong, how to undo.
```

## Cold Start Summary (Quick Reference)

```bash
# 1. Start stack
docker compose up -d

# 2. Run migrations
docker compose run --rm api alembic -c api/alembic.ini upgrade head

# 3. Seed reference data
docker compose run --rm worker-ingest celery -A worker.worker_app call worker.tasks.reference_tasks.load_reference_data

# 4. Trigger initial ingest for a connector (e.g., PNCP)
docker compose run --rm worker-ingest celery -A worker.worker_app call worker.tasks.ingest_tasks.run_ingest --args='["pncp"]'

# 5. Monitor worker logs
docker compose logs -f worker-ingest worker-normalize worker-cpu
```
