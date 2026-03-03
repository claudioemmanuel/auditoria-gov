# AuditorIA Gov Architecture

This document is the public architecture/specification baseline for AuditorIA Gov.
It replaces internal planning artifacts under `docs/plans/` for open-source publication.

## Mission

AuditorIA Gov is a public-read citizen auditing platform that ingests Brazilian federal open data, resolves entities across sources, detects reproducible corruption-risk patterns, and surfaces investigation-ready evidence.

## Core Principles

- Never claim corruption as fact; produce investigable risk signals.
- Every signal must carry reproducible evidence and numeric factors.
- LGPD by design: no raw CPF persistence in canonical storage.
- Deterministic detection: typologies are statistical/rule-based.
- LLM usage (optional) is explanatory only, never scoring.

## System Components

- `web/` (Next.js): Public portal for exploration, radar, and case views.
- `api/` (FastAPI): Public and internal endpoints.
- `worker/` (Celery): Ingestion, normalization, ER, baselines, and signal generation.
- `shared/`: Domain logic shared by API and workers.
- `postgres` (with pgvector): Canonical and analytical persistence.
- `redis`: Cache and Celery broker/result backend.

## Data Pipeline

1. Ingestion (`worker.tasks.ingest_tasks`)
   - Pulls enabled jobs from connector registry.
   - Stores raw payloads and run state.
2. Normalization (`worker.tasks.normalize_tasks`)
   - Maps source payloads into canonical entities/events/edges.
3. Entity Resolution (`worker.tasks.er_tasks`)
   - Matching + clustering across aliases/identifiers.
4. Baselines (`worker.tasks.baseline_tasks`)
   - Computes statistical reference baselines.
5. Typologies (`worker.tasks.signal_tasks`)
   - Runs T01-T10 deterministic detectors.
6. Coverage (`worker.tasks.coverage_tasks`)
   - Updates freshness and registry visibility.

## Sources and Connectors

Current ingestion runs through connector modules in `shared/connectors/`:

- `portal_transparencia`
- `pncp`
- `compras_gov`
- `comprasnet_contratos`
- `transferegov`
- `camara`
- `senado`
- `tse`
- `receita_cnpj`
- `querido_diario`

These connectors expose multiple jobs; together they provide the 11 public-source coverage described in the README.

## Typology Engine

Registered in `shared/typologies/registry.py`:

- T01 concentration
- T02 low competition
- T03 splitting
- T04 amendments outlier
- T05 price outlier
- T06 shell company proxy
- T07 cartel network
- T08 sanctions mismatch
- T09 ghost payroll proxy
- T10 outsourcing parallel payroll

## Privacy and LGPD

- CPF handling uses hashed or masked representation for cross-source linkage.
- Sensitive raw data should not be committed or exposed in repository artifacts.
- `.env`, local secrets, and bulk data directories remain gitignored.

## Operations

### Local stack

```bash
docker compose up --build
docker compose run --rm api alembic -c api/alembic.ini upgrade head
```

### Core verification

```bash
uv run --extra test pytest -q
```

## Public-Facing Documentation Set

- `README.md`: onboarding and usage
- `CONTRIBUTING.md`: contributor workflow
- `SECURITY.md`: vulnerability reporting policy
- `CODE_OF_CONDUCT.md`: contributor standards
- `CLAUDE.md`: Claude Code contributor guidance
