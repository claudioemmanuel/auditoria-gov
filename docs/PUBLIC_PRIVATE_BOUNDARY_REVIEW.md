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

---

## 2026-04-09 Follow-up — `shared/` tree deleted in both repos

The pre-split `shared/` namespace package has now been fully removed from both repos. All imports were migrated to the uv workspace packages that were already declared in `pyproject.toml`.

### Summary of the 6 phases

| Phase | Scope | Commits |
|---|---|---|
| 1 | Delete dead code: `shared/models/orm.py` stub, legacy `openwatch-core/api/` directory, cross-repo `apps/web` symlink, obsolete `web:` compose service | `923141d` (public), `f9d4e8d` (core) |
| 2 | Migrate `openwatch-core/shared/` → workspace packages; delete 88 files; rewrite 43 imports across worker + alembic env | `f072f9d`, `8d26b32`, `ae1eec7` (core) |
| 3 | Migrate `openwatch/shared/` → workspace packages; delete 33 files + legacy duplicate `tests/utils/`; move `shared/db.py` → `api/app/db.py`, `shared/models/{typology_catalog,public_filter}.py` → `packages/models/openwatch_models/`; drop `COPY openwatch/shared` from 3 Dockerfiles | `3849cf3` (public), `2909811` (core) |
| 4 | Delete `openwatch/api/alembic/` (25 migrations, all byte-identical duplicates of openwatch-core's) | `e96c5fe` (public) |
| 5 | Rewrite `tools/check_boundaries.py` to enforce workspace package boundaries instead of legacy `shared.*`; add `tests/public/test_boundary_hygiene.py` regression suite | `506deea` (public) |
| 6 | Docs/license polish: this follow-up section, `ARCHITECTURE.md` schema-ownership note, ADR updates | (this commit) |

### Final boundary state

- `openwatch/shared/` — **deleted**
- `openwatch-core/shared/` — **deleted**
- `openwatch/api/alembic/` — **deleted**
- `openwatch-core/apps/api/alembic/` — **sole owner** of the schema
- Public API surface: 39 Python files, 0 boundary violations (`check_boundaries.py --strict`)
- Import-linter: 3 contracts kept, 0 broken
- pytest public: 112 passed (108 + 4 new hygiene regressions)
- pytest openwatch-core: 12 passed
- Live container smoke tests: 2 clean rebuild+recreate cycles (Phase 2 + Phase 3), 59 Celery tasks registered, pipeline processing real data

### Production impact of the cleanup

During the Phase 2 live rebuild, the drained normalize pipeline uncovered a pre-existing `value too long for type character varying(100)` error on the `event` table when datajud tried to insert `assuntos[0].nome` values up to 121 chars. Migration `202604090200_widen_event_type_subtype` widens `event.type` and `event.subtype` from varchar(100) to varchar(255), matching the precedent set by `202604041550` for `event.source_connector`. The normalize backlog (5.4M rows from tce_rj that had been stalled behind the datajud error) drained by 359k rows in the first two minutes after the fix landed.

### Enforcement going forward

- CI must run `tools/check_boundaries.py --strict` and `lint-imports` on every PR to the public repo. Both are already wired into the pytest regression suite via `tests/public/test_boundary_hygiene.py`.
- Any new investigative logic continues to land in `openwatch-core` first.
- Public endpoints continue to talk to `openwatch-core` only through `api/core_client.py`.
- The `api/app/routers/internal.py` file is **live** (not dead). It proxies operator endpoints (`/internal/pipeline/status` etc.) to openwatch-core via `CoreClient`. An earlier revision of this doc claimed it had been removed; that was corrected in the 2026-04-09 cleanup.
