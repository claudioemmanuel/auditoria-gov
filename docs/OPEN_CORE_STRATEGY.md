# OpenWatch — Open-Core Strategy

This document defines what is open, what is protected, and why. It is the canonical reference for the open-core split between `openwatch` (public) and `openwatch-core` (private).

---

## What Is Open (MIT License)

The following components are publicly available and free to use, fork, and contribute to:

| Component | Path | Purpose |
|-----------|------|---------|
| Web Frontend | `web/` | Next.js public portal |
| Public API Router | `api/app/routers/public.py` | Read-only, filtered results only |
| TypeScript SDK | `packages/sdk/` | Client library for API consumers |
| UI Components | `packages/ui/` | Reusable React components |
| Generic Utilities | `packages/utils/`, `packages/config/` | Shared helpers |
| Public Data Models | `shared/models/canonical.py`, `signals.py`, `vocabulary.py`, `base.py` | Output schemas |
| Generic Connectors | `shared/connectors/ibge.py`, `brasilapi_cnpj.py`, `pncp.py`, `portal_transparencia.py`, `compras_gov.py`, `comprasnet_contratos.py` | Public government API wrappers |
| HTTP Client | `shared/connectors/http_client.py`, `domain_guard.py` | Generic HTTP tooling |
| Logging | `shared/logging.py` | Structured logging setup |
| Documentation | `docs/`, `README.md`, `CONTRIBUTING.md` | Community and contributor docs |
| Dev Tooling | `Makefile`, `docker-compose.dev-lite.yml`, CI configs | Local development support |
| DB Migrations | `api/alembic/` | Public schema definition |

---

## What Is Protected (BSL 1.1 License — `openwatch-core`)

The following components are **source-available** but **not permitted for competitor production use**. They reside in the private `openwatch-core` repository.

### Typology Engine — T01–T28

All corruption-risk detection algorithms are protected. These represent the primary intellectual property of OpenWatch.

```
shared/typologies/
├── base.py               # Abstract typology interface
├── registry.py           # Typology registry + runner
├── confidence_scorer.py  # Scoring engine
├── factor_metadata.py    # Factor weighting
├── t01_concentration.py  # Supplier concentration
├── t02_low_competition.py
├── t03_splitting.py
├── t04_amendments_outlier.py
├── t05_price_outlier.py
├── t06_shell_company_proxy.py
├── t07_cartel_network.py
├── t08_sanctions_mismatch.py
├── t09_ghost_payroll_proxy.py
├── t10_outsourcing_parallel_payroll.py
├── t11_spreadsheet_manipulation.py
├── t12_directed_tender.py
├── t13_conflict_of_interest.py
├── t14_compound_favoritism.py
├── t15_false_sole_source.py
├── t16_budget_clientelism.py
├── t17_layered_money_laundering.py
├── t18_illegal_position_accumulation.py
├── t19_bid_rotation.py
├── t20_phantom_bidders.py
├── t21_collusive_cluster.py
├── t22_political_favoritism.py
├── t23_bim_cost_overrun.py
├── t24_me_epp_quota_fraud.py
├── t25_tcu_condemned.py
├── t26_state_penalty_mismatch.py
├── t27_bndes_loan_nexus.py
└── t28_judicial_precedent_warning.py
```

### Risk Analytics

```
shared/analytics/
├── risk_score.py    # Composite risk scoring algorithm
└── benford.py       # Benford's Law statistical detector
```

### Entity Resolution

```
shared/er/
├── matching.py       # Fuzzy name/document matching
├── clustering.py     # Entity cluster assignment
├── normalize.py      # Name normalization pipeline
├── edges.py          # Graph edge construction
├── corporate_edges.py
└── confidence.py
```

### AI Pipeline

```
shared/ai/
├── classify.py    # Document classification
├── embeddings.py  # Vector embedding generation
├── ner.py         # Named entity recognition
├── rag.py         # Retrieval-augmented generation
├── explain.py     # Signal explanation (explanatory only)
└── provider.py    # LLM provider abstraction
```

### Baselines & Statistical Models

```
shared/baselines/
├── compute.py   # Baseline computation (percentiles, z-scores)
└── models.py    # Baseline ORM models
```

### Core Services

```
shared/services/
├── case_builder.py      # Evidence assembly and case generation
├── legal_inference.py   # Legal hypothesis generation
├── alerts.py            # Risk alert routing
├── infra_alerts.py      # Infrastructure monitoring alerts
└── reference_seed.py    # Reference data seeding
```

### Internal Data Access

```
shared/repo/
├── queries.py       # All analytical queries
├── upsert.py        # Async upsert strategies
├── upsert_sync.py
└── provenance.py    # Evidence chain queries
```

### Worker Tasks (Full Pipeline)

```
worker/tasks/
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
├── backfill_cpf.py      # LGPD backfill
└── __init__.py
```

### Enrichment Connectors (Data Strategy)

```
shared/connectors/
├── veracity.py        # Veracity scoring
├── bacen.py           # Brazilian Central Bank
├── datajud.py         # CNJ judicial data
├── tce_pe/rj/rs/sp.py # State audit courts
├── tcu.py             # Federal audit court
├── tse.py             # Electoral court
├── camara.py          # Chamber of Deputies
├── senado.py          # Senate
├── bndes.py           # National development bank
├── jurisprudencia.py  # Legal precedents
├── querido_diario.py  # Official gazette
├── transferegov.py    # Federal transfers
├── anvisa_bps.py      # Health data
├── receita_cnpj.py    # Tax registry bulk data
└── orcamento_bim.py   # Budget data
```

### Internal API, Scheduler, Infrastructure

```
api/app/routers/internal.py   # Internal endpoints (never public)
shared/scheduler/schedule.py  # Pipeline orchestration schedule
infra/                        # AWS/Terraform/Caddy configs
docker-compose.yml            # Full stack (internal only)
docker-compose.prod.yml       # Production stack
```

---

## Architecture: Execution Model

```
┌─────────────────────────────────────────────────────────┐
│                   PUBLIC INTERNET                        │
└──────────────────────┬──────────────────────────────────┘
                       │
             ┌─────────▼──────────┐
             │   openwatch (MIT)  │
             │  Next.js Frontend  │
             │  Public API Router │
             │  (gateway only)    │
             └─────────┬──────────┘
                       │  HTTPS / service mesh (internal only)
             ┌─────────▼──────────────────────────────────┐
             │        openwatch-core (BSL 1.1)             │
             │  Internal API Router                         │
             │  Typology Engine (T01–T28)                   │
             │  Entity Resolution                           │
             │  Risk Scoring                                │
             │  Data Pipelines (Celery Workers)             │
             │  Enrichment Connectors (20+)                 │
             └─────────┬──────────────────────────────────┘
                       │
             ┌─────────▼──────────┐
             │  PostgreSQL + Redis │
             │  (private network) │
             └────────────────────┘
```

**Critical:** The core service runs **only on controlled infrastructure**. The public API delegates to it via `api/core_client.py`. No typology, scoring, or enrichment logic ever executes in the public layer.

---

## Licensing

| Layer | License | Terms |
|-------|---------|-------|
| `openwatch` (public) | MIT | Free use, fork, modify, redistribute |
| `openwatch-core` (private) | BSL 1.1 | Source-available; **no competitor production use**; converts to Apache 2.0 after 4 years from file commit date |

See `LICENSE` (public repo) and `LICENSE-BSL` (core repo) for full terms.

---

## Boundary Enforcement

The `tools/check_boundaries.py` script enforces that public-layer files never import protected modules. It runs automatically on every pull request via `.github/workflows/boundary-check.yml`.

```bash
# Run manually
python tools/check_boundaries.py

# Strict mode (connector warnings = errors)
python tools/check_boundaries.py --strict

# List all protected modules
python tools/check_boundaries.py --list-protected
```

---

## Contribution Scope

Community contributions are welcome in the **public layer only**:
- Web frontend improvements
- SDK enhancements
- Documentation
- Generic connector fixes (for the 6 public connectors)
- Bug reports and security disclosures

Contributions to the typology engine, risk scoring, or entity resolution logic are managed internally and are not accepted via public PRs.

See `CONTRIBUTING.md` for details.

---

## Anti-Replication Posture

| Asset | Protection Method |
|-------|------------------|
| Typology algorithms (T01–T28) | Private repo + BSL 1.1 |
| Entity resolution logic | Private repo + BSL 1.1 |
| Enrichment connector strategy | Private repo; connectors are data-source-specific |
| Historical enriched datasets | Not published; infrastructure-side only |
| Risk scoring weights | Server-side execution only; never exposed in API |
| Pipeline schedule & orchestration | Private repo |
| Infrastructure topology | Private repo (infra/) |

Replication cost: a competitor would need to independently develop 28 typology algorithms, a multi-source entity resolution system, 20+ specialized government data connectors, and a risk scoring model — without access to the historical calibration data that shapes the current weights.
