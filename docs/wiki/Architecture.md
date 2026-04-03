# Architecture

## High-Level Flow

1. Connector ingestion fetches raw data into `raw_source`
2. Normalization maps records into canonical entities/events
3. Entity resolution clusters aliases and links nodes; `resolve_entity_ids_with_clusters()` bridge expands pre-merge UUIDs cluster-wide in all signal query paths
4. Baseline computation builds statistical references
5. Typology engine runs deterministic detectors (T01-T18)
6. Public API serves radar, entity search, path explanation, case, org, and signal views

## Components

- `web/` - Next.js frontend (includes data quality coverage page)
- `api/` - FastAPI public/internal endpoints
- `worker/` - Celery tasks and schedules
- `shared/` - domain logic shared across services
- `postgres` (+ `pg_trgm`, `pgvector`) - canonical and analytics storage
- `redis` - cache + queue broker/backend

## Key API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /public/entity/search` | Fuzzy entity search (`pg_trgm`), LGPD-scoped for persons |
| `GET /public/graph/path` | Shortest path between entities (recursive CTE, ≤10 hops) |
| `GET /public/sources` | Veracity registry and compliance status |
| `GET /internal/data-quality` | Data quality dashboard: per-source stats, overlap histogram, drop alerts |

## Scheduling

The pipeline is orchestrated by Celery Beat (incremental ingest, ER, baselines, signals, coverage refresh, maintenance).

## Design Rules

- Deterministic detection only
- Explainability over opaque scoring
- Source-traceable evidence paths
- Privacy safeguards by default
