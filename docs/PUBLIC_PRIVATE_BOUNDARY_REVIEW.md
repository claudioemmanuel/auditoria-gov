# Public/Private Boundary Review

_Date: 2026-04-03_

## Scope reviewed

- Public repo: `openwatch`
- Private repo: `openwatch-core`

## Architecture decision

The split is now treated as **final**:

- `openwatch` keeps the **public web app**, the **public API gateway**, public docs, and public-facing schemas/utilities.
- `openwatch-core` owns **ingestion**, **analytics**, **entity resolution**, **typology execution**, **workers**, and **private infrastructure**.

## What was identified as dead or misplaced in the public repo

### Dead transitional code
- Duplicate backend implementation under `apps/api/`
- Internal-only router under `api/app/routers/internal.py`
- Dual-mode fallback code in `api/app/adapters/core_adapter.py`
- Unused split scaffold `api/app/adapters/split_ready_adapter.py`

### Private-core code that belonged in `openwatch-core`
- `core/`
- `worker/`
- `infra/`
- `packages/db/`
- protected connector implementations
- protected `shared/*` domains (`ai`, `analytics`, `baselines`, `er`, `repo`, `scheduler`, `services`, `typologies`)
- ORM/raw model definitions used by the private ingestion pipeline
- non-public test suites for core and worker internals

## Public layer that remains in `openwatch`

- `apps/web/`
- `api/` public gateway surface
- `packages/config/`
- `packages/utils/`
- public model/schema packages
- public docs and contribution files
- generic connector boundary helpers (`domain_guard`, `http_client`)

## Security notes from the review

- Internal endpoint wiring was removed from the public API app.
- The public repo no longer ships the private router implementation.
- The legacy development `INTERNAL_API_KEY` default was removed from the public environment example and config defaults.

## Follow-up guidance

- Any new investigative logic should land in `openwatch-core` first.
- Public endpoints should talk to `openwatch-core` only through `api/core_client.py`.
- Boundary checks in `tools/check_boundaries.py` should remain part of CI to prevent regressions.
