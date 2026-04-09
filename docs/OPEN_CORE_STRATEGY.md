# Open Core Strategy

OpenWatch uses an **open-core** model to balance transparency with sustainability.

## Repository Structure

| Repo | Visibility | License | Contents |
|------|-----------|---------|----------|
| [openwatch](https://github.com/openwatch-br/openwatch) | Public | MIT | Frontend, public API gateway, public schemas, docs |
| [openwatch-core](https://github.com/openwatch-br/openwatch-core) | Private | BSL 1.1 | Analytics engine, typologies, ER, workers, infrastructure |

## Why Open Core?

OpenWatch's mission is civic accountability. Full transparency of *what* is being detected (typology definitions, data sources) is essential for public trust. However, commercial-grade implementations of the analytics engine represent significant R&D investment.

The BSL 1.1 license on `openwatch-core`:
- Allows non-commercial research, journalism, academic study, and civic auditing
- Restricts competing commercial use until the change date (4 years)
- Automatically converts to Apache 2.0 on the change date

## Public Boundary

The following ALWAYS live in the public (`openwatch`) repo:
- Public API surface (`/public/*` endpoints)
- Next.js frontend
- Public typology catalog (names, descriptions, legal citations)
- Generic connector helpers (domain guard, HTTP client base)
- Shared config and utility packages
- Documentation and contribution guides

The following ALWAYS live in the private (`openwatch-core`) repo:
- Typology scoring logic (implementations)
- Entity resolution algorithms
- AI/LLM integration
- Celery pipeline workers
- Government API connector implementations
- Database ORM models
- Private infrastructure (Terraform, Caddy)

## Boundary Enforcement

Three layers of enforcement prevent the public layer from importing private-layer code directly:

1. **`tools/check_boundaries.py --strict`** — AST-based static check that walks every public Python file (`api/app/*`, `packages/{config,utils,models,connectors}`, `api/core_client.py`) and fails the build if it finds any import of a protected workspace package (`openwatch_ai`, `openwatch_analytics`, `openwatch_baselines`, `openwatch_er`, `openwatch_pipelines`, `openwatch_queries`, `openwatch_scheduler`, `openwatch_services`, `openwatch_typologies`, `openwatch_db`) or a protected gov-API connector implementation (18 modules under `openwatch_connectors.*`). Lives at `tools/check_boundaries.py`.
2. **`.import-linter`** — 3 contracts enforced by the `lint-imports` CLI: (a) public packages (`openwatch_config`, `openwatch_utils`, `openwatch_models`, `openwatch_connectors`, `app`) must not import core detection modules; (b) the `app` package (FastAPI gateway) must not import typologies, ER, analytics, or baselines directly; (c) `openwatch_config` must not create a circular dependency by importing `openwatch_utils`, `openwatch_models`, or `openwatch_connectors`.
3. **`tests/public/test_boundary_hygiene.py`** — pytest regression suite that asserts (a) `shared/` does not exist, (b) `api/alembic/` does not exist, (c) `check_boundaries.py --strict` exits 0, and (d) no `from shared.` / `import shared.` statement (top-level or indented) exists anywhere in `api/`, `packages/`, or `tests/public/`. Runs as part of the normal `make test` suite.

## 2026-04-09 Post-cleanup state

The pre-split `shared/` namespace package has been fully removed from both repos. All imports were migrated to the `uv` workspace packages that were already declared in `pyproject.toml`. See `docs/PUBLIC_PRIVATE_BOUNDARY_REVIEW.md` for the full 6-phase audit + commit list.
