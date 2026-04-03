# Coding Rules — OpenWatch

## Async-First

- All database access must use `async with session` (SQLAlchemy async).
- Never use `db_sync.py` in new code paths; it exists only for maintenance_tasks.py compatibility.
- Use `asyncpg` directly for bulk inserts; use `execute_chunked_in` from `shared/utils/query.py` for IN queries with >5 000 participants.

## Outbound HTTP

- Every outbound HTTP call must pass through `shared/connectors/domain_guard.py`.
- Non-government domains require a `DomainException` with written justification and a review date.
- No direct `httpx`, `requests`, or `urllib` calls outside of `shared/connectors/`.

## LLM Usage

- LLM calls are **explanatory only** — they must never affect risk scoring or signal creation.
- All functions that call an LLM must be decorated with `@explanatory_only` from `shared/ai/provider.py`.
- Do not add new LLM dependencies; use the provider abstraction in `shared/ai/provider.py`.

## Data Models

- Use Pydantic v2 everywhere. No `.dict()` — use `.model_dump()` and `.model_validate()`.
- SQLAlchemy ORM models live in `shared/models/`. No inline schema definitions in routers.
- New event types follow the existing pattern: model → connector → normalize → migrate.

## Database Migrations (Alembic)

- Never use `CREATE INDEX CONCURRENTLY` inside Alembic migration functions — Alembic runs inside a transaction.
- Migration files go in `api/alembic/versions/`. Run: `docker compose run --rm api alembic -c api/alembic.ini upgrade head`.

## Typology Logic

- Typologies must be deterministic and auditable — same inputs must always produce the same signals.
- Use 5-year event windows minimum to capture historical PNCP data (2021 baseline).
- Register every new typology in `shared/typologies/registry.py`.

## New Connectors

- Add to `shared/connectors/` + update `shared/connectors/__init__.py`.
- Provide a `SourceVeracityProfile` in `shared/connectors/veracity.py`.
- Update `docs/GOVERNANCE.md` with the new source.
