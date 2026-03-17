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
   - Runs T01-T22 deterministic detectors.
6. Coverage (`worker.tasks.coverage_tasks`)
   - Updates freshness and registry visibility.

## Public API Endpoints

### Public (unauthenticated)

- `GET /public/radar` — Risk signal radar with filters
- `GET /public/entity/search?q=<text>&type=company|person&limit=20` — Fuzzy entity search via pg_trgm (GIN index on `name_normalized`). Person results are LGPD-scoped to public-servant connectors via `EntityRawSource` join.
- `GET /public/graph/path?from=<id>&to=<id>&max_hops=5` — Shortest path between two entities using a PostgreSQL recursive CTE; returns node/edge list with `event_type`, `typology_ids`, `first_seen`, and `last_seen` per edge.
- `GET /public/sources` — Source veracity registry (scores, compliance status, freshness)
- `GET /signal/{id}/provenance` — Full evidence chain for a signal
- `GET /case/{id}/provenance` — Full evidence chain for a case

### Internal (authenticated)

- `GET /internal/data-quality` — Data quality monitoring: per-source entity count, freshness lag, veracity score, cross-source entity overlap histogram, and week-over-week contribution delta alerts (>20% drop threshold).

## Entity Resolution Bridge

`resolve_entity_ids_with_clusters(session, raw_entity_ids)` in `shared/repo/queries.py` expands any list of entity UUIDs to the full cluster — entities sharing the same `cluster_id` after an ER merge. This bridge is applied to all signal-matching query paths (`get_org_summary`, case graph, `compute_entity_risk_score`, radar listing) so that signals filed against pre-merge entity UUIDs are correctly surfaced after ER runs. The helper is batch-safe: always called once per request, never in a per-signal loop.

## Database Extensions

- `pgvector`: embeddings support
- `pg_trgm`: trigram similarity index on `entity.name_normalized` (migration `0014`) for fuzzy bulk entity search

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
- T11 jogo de planilha
- T12 edital direcionado
- T13 conflito de interesses
- T14 sequência de favorecimento (meta-typology)
- T15 inexigibilidade indevida
- T16 clientelismo orçamentário (emenda pix)
- T17 lavagem via camadas societárias
- T18 acúmulo ilegal de cargos
- T19 bid rotation
- T20 phantom bidders
- T21 collusive cluster
- T22 political favoritism

## Worker Architecture

The Celery task queue is split into two worker containers with distinct queue assignments and resource profiles:

| Worker | Queues | Concurrency | Memory Limit | Role |
|--------|--------|-------------|--------------|------|
| `worker-primary` | `ingest`, `normalize`, `ai`, `default`, `vacuum` | 2 | — | High-throughput ingestion + Beat scheduler |
| `worker-heavy` | `er`, `signals`, `bulk`, `default` | 1 | 2 GB | CPU/memory-intensive ER and signal generation |

`worker-primary` also runs the Celery Beat scheduler. `worker-heavy` handles entity resolution (advisory-locked singleton) and typology signal runs, which can process hundreds of thousands of participants per wave.

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

### AWS Production Deployment

Production runs on AWS ECS Fargate with the following topology:

```
CloudFront → S3 (Next.js static export)
ALB → ECS Fargate (API service, always-on)
EventBridge Scheduler → ECS Fargate (Worker one-shot tasks, on-demand)
ECS → RDS PostgreSQL 17 + pgvector (db.t3.micro)
ECS → ElastiCache Redis 7.1 (cache.t3.micro)
```

Infrastructure is managed by Terraform in `infra/aws/`. Deploy with:

```bash
cd infra/aws
cp terraform.tfvars.example terraform.tfvars
# Fill in secrets — see docs/DEPLOYMENT.md
terraform init && terraform apply
```

Worker containers run as one-shot Fargate tasks triggered by EventBridge Scheduler:

- `pipeline-full` — daily 03:00 UTC (full ingest + ER + signals)
- `pipeline-bulk` — daily 00:00 UTC (bulk connector refresh)
- `pipeline-maintenance` — Sunday 02:00 UTC (vacuum, coverage update)

CI/CD: `.github/workflows/deploy.yml` uses GitHub OIDC (no long-lived keys) to push images to ECR, update ECS task definitions, sync the frontend to S3, and run Alembic migrations via a one-shot ECS task.

**Budget guardrail:** A Lambda function triggered by AWS Budgets stops all ECS services, stops RDS, and disables EventBridge rules when spend reaches $20/month.

See `docs/DEPLOYMENT.md` and `docs/COST.md` for full details.

## Public-Facing Documentation Set

- `README.md`: onboarding and usage
- `CONTRIBUTING.md`: contributor workflow
- `SECURITY.md`: vulnerability reporting policy
- `CODE_OF_CONDUCT.md`: contributor standards
- `CLAUDE.md`: Claude Code contributor guidance
