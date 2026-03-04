# Current Status

Last updated: 2026-03-04

## Product Scope

- Public read-only web experience (no login required)
- FastAPI API + Celery workers + PostgreSQL + Next.js
- 10 connector modules ingesting 11 public source streams
- 18 deterministic typology detectors (T01-T18)

## Phase 6+ Features (shipped 2026-03-04)

- **Bulk entity search** — `GET /public/entity/search?q=&type=company|person` with pg_trgm fuzzy matching and LGPD-compliant person scoping
- **Path explanation API** — `GET /public/graph/path?from=&to=&max_hops=5` with recursive CTE shortest-path and temporal edge annotations
- **ER change-propagation bridge** — cluster-aware signal resolution across all query paths; `resolve_entity_ids_with_clusters()` applied to `get_org_summary`, case graph, risk scoring, and radar
- **Data quality monitoring** — `GET /internal/data-quality` with per-source stats, cross-source overlap histogram, and week-over-week drop alerts

## Engineering Status

- CI enabled and passing on `main` (556 tests)
- OSS governance baseline completed:
  - AGPL-3.0 license
  - Contributor covenant code of conduct
  - Contributing and security policies
  - Issue and PR templates
  - Contributor guidance for Claude Code
- `pg_trgm` extension + GIN index on `entity.name_normalized` (migration `0014`)

## Operational Status

- Full local stack available with Docker Compose
- Scheduled processing pipeline configured via Celery Beat
- Optional LLM explanation layer with deterministic fallback
- Data quality dashboard available at `/coverage/quality` (admin)

## Known Limits

- Some data sources require tokens and/or large local datasets
- Wiki git endpoint may require manual first-page initialization in GitHub UI before direct `.wiki.git` sync
