# Architecture

## High-Level Flow

1. Connector ingestion fetches raw data into `raw_source`
2. Normalization maps records into canonical entities/events
3. Entity resolution clusters aliases and links nodes
4. Baseline computation builds statistical references
5. Typology engine runs deterministic detectors (T01-T10)
6. Public API serves radar, case, entity, org, and signal views

## Components

- `web/` - Next.js frontend
- `api/` - FastAPI public/internal endpoints
- `worker/` - Celery tasks and schedules
- `shared/` - domain logic shared across services
- `postgres` - canonical and analytics storage
- `redis` - cache + queue broker/backend

## Scheduling

The pipeline is orchestrated by Celery Beat (incremental ingest, ER, baselines, signals, coverage refresh, maintenance).

## Design Rules

- Deterministic detection only
- Explainability over opaque scoring
- Source-traceable evidence paths
- Privacy safeguards by default
