# OpenWatch Architecture

Public architecture and design document for the OpenWatch platform.

---

## Open-Core Model

| Layer | Repository | License | Contains |
|-------|-----------|---------|---------|
| **Public** | `openwatch-br/openwatch` (this repo) | MIT | Frontend, public API gateway, 6 generic connectors, SDK, public models |
| **Protected Core** | `openwatch-br/openwatch-core` | BSL 1.1 | Typologies T01–T28, risk scoring, entity resolution, 17 enrichment connectors, data pipelines |

See [`docs/OPEN_CORE_STRATEGY.md`](OPEN_CORE_STRATEGY.md) for the full file-by-file classification.

---

## Mission

OpenWatch is a public-read citizen auditing platform that:

1. Ingests 23 Brazilian federal open-data sources
2. Resolves entities across sources using CNPJ, CPF (hashed), and name matching
3. Applies 28 deterministic corruption-risk typologies
4. Surfaces reproducible, evidence-linked investigation signals via a public portal

**Core principle:** Never claim corruption as fact; produce investigable risk signals.
Every signal carries numeric factors and links to the raw evidence.

---

## Repository Structure

```
openwatch/
├── apps/
│   ├── api/          # FastAPI public API gateway (canonical)
│   └── web/          # Next.js public portal (canonical)
├── packages/
│   ├── config/       # Settings and environment (openwatch-config)
│   ├── connectors/   # 6 public + 17 protected connectors (openwatch-connectors)
│   ├── db/           # Database access layer [PROTECTED] (openwatch-db)
│   ├── models/       # Data models, public + protected (openwatch-models)
│   ├── sdk/          # TypeScript client SDK
│   ├── ui/           # Reusable React UI components
│   └── utils/        # Python utilities (openwatch-utils)
├── core/             # Protected packages [PROTECTED]
│   ├── typologies/   # T01–T28 detectors (openwatch-typologies)
│   ├── analytics/    # Risk scoring, Benford (openwatch-analytics)
│   ├── er/           # Entity resolution (openwatch-er)
│   ├── baselines/    # Statistical baselines (openwatch-baselines)
│   ├── services/     # Case builder, legal inference (openwatch-services)
│   ├── queries/      # Analytical DB queries (openwatch-queries)
│   ├── pipelines/    # Celery worker tasks (openwatch-pipelines)
│   ├── scheduler/    # Beat schedule (openwatch-scheduler)
│   └── ai/           # LLM integration (openwatch-ai)
├── tests/
│   ├── public/       # Tests for the public layer (run in OSS CI)
│   └── core/         # Tests for core packages (run in private CI)
├── infra/
│   ├── aws/          # Terraform infrastructure [PROTECTED]
│   ├── caddy/        # Reverse proxy config [PROTECTED]
│   └── docker/       # Docker Compose files
└── tools/            # Dev and split automation scripts
```

> **Legacy note:** `shared/`, `api/` (root), and `worker/` directories are legacy
> copies maintained for backward compatibility during the monorepo-to-split transition.
> Canonical code lives in `packages/`, `core/`, and `apps/`.

---

## System Components

- `apps/web/` (Next.js 14): Public portal — radar, entity explorer, case investigation, dossiers
- `apps/api/` (FastAPI): Public and internal API endpoints; acts as gateway to core service
- `core/pipelines/` (Celery + Beat): Data ingestion, normalization, ER, baselines, signals
- PostgreSQL 17 + pgvector: Canonical storage + semantic search
- Redis: Celery broker, result backend, API cache

---

## Public API Endpoints

All endpoints are under `/public/` and require no authentication.

| Endpoint | Description |
|----------|-------------|
| `GET /public/radar` | Risk signal radar with filters |
| `GET /public/entity/search?q=<text>` | Entity fuzzy search (pg_trgm) |
| `GET /public/entity/{id}` | Entity detail |
| `GET /public/case/{id}` | Case detail with signals |
| `GET /public/signal/{id}` | Signal detail with evidence |
| `GET /public/graph/path` | Shortest path between entities |
| `GET /public/graph/neighborhood/{id}` | Entity neighborhood |
| `GET /public/coverage` | Data freshness summary |
| `GET /public/sources` | Active connector list |
| `POST /public/contestation` | Submit contestation on a signal |

Rate limit: 10 req/s, burst 30.

---

## Data Pipeline (runs in `openwatch-core`)

```
1. Ingest       connectors pull source data → raw_source table
2. Normalize    raw payloads → canonical entities/events/edges
3. Entity Res.  fuzzy matching + clustering across identifiers
4. Baselines    compute statistical reference baselines
5. Typologies   T01–T28 detectors → risk signals
6. Cases        group signals by entity cluster → investigation cases
7. Coverage     update freshness + registry visibility
```

---

## LGPD Compliance

- CPF values are never stored in canonical tables; only a HMAC-SHA256 hash
- The hash salt (`CPF_HASH_SALT`) is set once and never changed in production
- Person entity search is scoped to public-servant connectors
- No raw personal data is surfaced via the public API

---

## Security Model

| Component | Protection |
|-----------|-----------|
| Public API | Rate limited, no authentication required, read-only |
| Internal API | Requires `X-Internal-Api-Key` header |
| Core service | Not exposed to public internet; reached only via internal network |
| Infrastructure | AWS VPC, private subnets, IAM least-privilege (Terraform in `infra/aws/`) |
| Secrets | AWS Secrets Manager in production; `.env` locally |

---

## Open-Core Boundary

The `tools/check_boundaries.py` script enforces that the public API layer never imports
from protected modules. This runs on every PR:

```bash
uv run python tools/check_boundaries.py
```

See [`OPEN_CORE_STRATEGY.md`](OPEN_CORE_STRATEGY.md) for the complete boundary rules.
