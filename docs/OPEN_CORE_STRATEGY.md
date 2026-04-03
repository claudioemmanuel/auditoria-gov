# OpenWatch — Open-Core Strategy

This document defines what is open, what is protected, and why.
It is the canonical reference for the open-core split between
`openwatch-br/openwatch` (public, MIT) and `openwatch-br/openwatch-core` (private, BSL 1.1).

> **Note on architecture:** The repository has been refactored from a legacy `shared/`
> monolith to a canonical `packages/` + `core/` + `apps/` workspace structure. Both
> structures coexist during the transition. The classification below covers the **canonical**
> paths. The split script (`tools/split_repo.sh`) handles both.

---

## What Is Open — `openwatch-br/openwatch` (MIT)

| Component | Canonical path | Purpose |
|-----------|---------------|---------|
| Web portal | `apps/web/` | Next.js public investigation interface |
| Public API router | `apps/api/app/routers/public.py` | Read-only filtered endpoints |
| API app scaffold | `apps/api/app/` (excl. `routers/internal.py`) | FastAPI app, middleware, deps |
| DB migrations | `apps/api/alembic/` | Public schema (all tables) |
| Config package | `packages/config/` | Environment / settings |
| Utilities package | `packages/utils/` | CNPJ, hashing, rate limit, text, time, sync helpers |
| Public models | `packages/models/openwatch_models/` excl. `orm.py`, `raw.py`, `radar.py` | API response schemas, coverage, graph |
| Public connectors (6) | `packages/connectors/openwatch_connectors/` — `ibge`, `brasilapi_cnpj`, `pncp`, `portal_transparencia`, `compras_gov`, `comprasnet_contratos`, `http_client`, `domain_guard`, `base` | Public government API wrappers |
| TypeScript SDK | `packages/sdk/` | Client library for API consumers |
| UI components | `packages/ui/` | Reusable React components |
| Public tests | `tests/public/` | Tests for the public layer |
| Documentation | `docs/`, `README.md`, `CONTRIBUTING.md`, etc. | Community-facing docs |
| Dev tooling | `Makefile`, `infra/docker/docker-compose.dev-lite.yml` | Local dev support |

---

## What Is Protected — `openwatch-br/openwatch-core` (BSL 1.1)

### Typology Engine — T01–T28

All 28 corruption-risk detectors. These represent the primary intellectual property of the project.

```
core/typologies/openwatch_typologies/
├── base.py                # Abstract typology interface
├── registry.py            # Typology registry + runner
├── confidence_scorer.py   # Scoring engine
├── factor_metadata.py     # Factor weighting
├── t01_concentration.py   # Supplier concentration
├── t02_low_competition.py
├── t03_splitting.py
...
└── t28_judicial_precedent_warning.py
```

### Risk Analytics

```
core/analytics/openwatch_analytics/
├── risk_score.py   # Composite risk scoring algorithm
└── benford.py      # Benford's Law statistical detector
```

### Entity Resolution

```
core/er/openwatch_er/
├── matching.py        # Fuzzy name/document matching
├── clustering.py      # Entity cluster assignment
├── normalize.py       # Name normalization pipeline
├── edges.py           # Graph edge construction
├── corporate_edges.py
└── confidence.py
```

### AI Pipeline (explanatory only)

```
core/ai/openwatch_ai/
├── classify.py    # Document classification
├── embeddings.py  # Vector embedding generation
├── ner.py         # Named entity recognition
├── rag.py         # Retrieval-augmented generation
├── explain.py     # Signal explanation (LLM — never scoring)
└── provider.py    # LLM provider abstraction
```

### Baselines & Statistical Models

```
core/baselines/openwatch_baselines/
├── compute.py   # Baseline computation (percentiles, z-scores)
└── models.py    # Baseline ORM models
```

### Core Services

```
core/services/openwatch_services/
├── case_builder.py      # Evidence assembly and case generation
├── legal_inference.py   # Legal hypothesis generation
├── alerts.py            # Risk alert routing
├── infra_alerts.py      # Infrastructure monitoring
└── reference_seed.py    # Reference data seeding
```

### Internal Queries

```
core/queries/openwatch_queries/
└── queries.py   # All analytical DB queries
```

### Database Access Layer

```
packages/db/openwatch_db/
├── db.py          # Async session factory
├── db_sync.py     # Sync session factory (worker)
├── upsert.py      # Async upsert strategies
├── upsert_sync.py
└── provenance.py  # Evidence chain queries
```

### Internal Models

```
packages/models/openwatch_models/
├── orm.py          # SQLAlchemy ORM models (all tables)
├── raw.py          # Raw ingestion data models
├── radar.py        # Risk signal radar response types
└── public_filter.py  # Public API filtering helpers
```

### Data Pipelines (Celery Worker)

```
core/pipelines/openwatch_pipelines/
├── ingest_tasks.py      # Raw data ingestion
├── normalize_tasks.py   # Canonicalization
├── er_tasks.py          # Entity resolution runs
├── baseline_tasks.py    # Baseline computation
├── signal_tasks.py      # Typology execution → risk signals
├── case_tasks.py        # Case generation
├── coverage_tasks.py    # Coverage tracking
├── ai_tasks.py          # AI processing
├── compliance_tasks.py  # Compliance checks
├── reference_tasks.py   # Reference data
├── maintenance_tasks.py # DB vacuum + cleanup
└── backfill_cpf.py      # LGPD backfill
```

### Scheduler

```
core/scheduler/openwatch_scheduler/
└── schedule.py   # Pipeline orchestration schedule
```

### Enrichment Connectors (17 protected)

```
packages/connectors/openwatch_connectors/
├── veracity.py        # Veracity scoring
├── bacen.py           # Brazilian Central Bank
├── datajud.py         # CNJ judicial data
├── tce_pe/rj/rs/sp.py # State audit courts (4)
├── tcu.py             # Federal audit court
├── tse.py             # Electoral court
├── camara.py          # Chamber of Deputies
├── senado.py          # Senate
├── bndes.py           # National development bank
├── jurisprudencia.py  # Legal precedents
├── querido_diario.py  # Official gazette
├── transferegov.py    # Federal transfers
├── anvisa_bps.py      # Health pricing
├── receita_cnpj.py    # Tax registry bulk data
└── orcamento_bim.py   # Budget data
```

### Internal API, Infrastructure, Production Stack

```
apps/api/app/routers/internal.py   # Internal-only endpoints
infra/aws/                         # Terraform (AWS)
infra/caddy/                       # Reverse proxy config
infra/docker/docker-compose.yml    # Full production stack
infra/docker/docker-compose.prod.yml
```

---

## Architecture: Execution Model

```
┌──────────────────────────────────────────────┐
│              PUBLIC INTERNET                  │
└──────────────────────┬───────────────────────┘
                       │
             ┌─────────▼──────────┐
             │  openwatch (MIT)   │
             │  Next.js Frontend  │
             │  Public API Router │
             │  (gateway only)    │
             └─────────┬──────────┘
                       │  HTTPS (CORE_SERVICE_URL)
             ┌─────────▼──────────────────────────┐
             │  openwatch-core (BSL 1.1)           │
             │  Internal API Router                 │
             │  Typology Engine (T01–T28)           │
             │  Entity Resolution                   │
             │  Risk Scoring                        │
             │  Data Pipelines (Celery Workers)     │
             │  Enrichment Connectors (20+)         │
             └─────────┬──────────────────────────┘
                       │
             ┌─────────▼──────────┐
             │  PostgreSQL + Redis │
             │  (private network) │
             └────────────────────┘
```

The core service runs **only on controlled infrastructure**. The public API calls it via
`CORE_SERVICE_URL` + `CORE_API_KEY`. No typology, scoring, or enrichment logic ever
executes in the public layer.

---

## Licensing

| Repository | License | Terms |
|-----------|---------|-------|
| `openwatch-br/openwatch` | **MIT** | Free use, fork, modify, redistribute |
| `openwatch-br/openwatch-core` | **BSL 1.1** | Source-available; no competitor production use; converts to Apache 2.0 after 4 years |

---

## Boundary Enforcement

`tools/check_boundaries.py` enforces that public files never import protected modules.
It runs on every PR via `.github/workflows/boundary-check.yml`.

```bash
uv run python tools/check_boundaries.py          # check
uv run python tools/check_boundaries.py --strict  # warnings = errors
```

---

## Executing the Split

When ready to physically separate the repos:

```bash
# 1. Run pre-flight checks
bash tools/split_repo_preflight.sh

# 2. Dry run — review output carefully
export GITHUB_TOKEN=$(gh auth token)
export GITHUB_OWNER=openwatch-br
bash tools/split_repo.sh --dry-run

# 3. Execute (irreversible)
bash tools/split_repo.sh
```

See `tools/split_repo.sh` for the full protected paths list.

---

## Contribution Scope

External contributions welcome in the **public layer only**.
See [CONTRIBUTING.md](../CONTRIBUTING.md) for details.
