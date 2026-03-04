# Roadmap

## Completed — Phase 6+ (Q1 2026)

- **6.1 ER Change-Propagation Bridge** — `resolve_entity_ids_with_clusters()` batch helper applied to all signal query paths; cluster-expanded results in `get_org_summary`, case graph, `compute_entity_risk_score`, and radar listing
- **6.2 Bulk Entity Search** — `GET /public/entity/search` with pg_trgm GIN index on `entity.name_normalized`; LGPD-scoped person search restricted to public-servant connector sources via `EntityRawSource`
- **6.3 Path Explanation API** — `GET /public/graph/path` with PostgreSQL recursive CTE, configurable `max_hops` (1–10), temporal bounds via `EventParticipant → Event.occurred_at` join
- **6.4 Data Quality Monitoring** — `GET /internal/data-quality` with per-source freshness/veracity, cross-source entity overlap histogram, week-over-week contribution delta alerts (>20% drop)

## Near-Term (Q2 2026)

- Expand source robustness and retry telemetry
- Increase typology coverage quality metrics and explainability
- Improve public investigation UX built on Phase 6.2/6.3 endpoints
- Entity Profile API (depends on bulk search — Phase 6.2 now complete)

## Mid-Term

- Add more government data connectors with deterministic normalization
- Improve quality scoring and provenance visualization
- Expand reproducibility artifacts for journalistic workflows

## Long-Term

- Multi-country portability of ingestion + typology engine
- Community-maintained detector packs
- Better civic newsroom collaboration workflows

## Maintenance Priorities

- Keep CI green
- Preserve deterministic behavior and reproducible outputs
- Enforce no-secrets and LGPD protections in contribution flow
