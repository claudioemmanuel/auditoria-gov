# OpenWatch

[![CI](https://github.com/openwatch-br/openwatch/actions/workflows/ci.yml/badge.svg)](https://github.com/openwatch-br/openwatch/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)
[![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)](./pyproject.toml)
[![Next.js](https://img.shields.io/badge/Next.js-14-black?logo=next.js)](./apps/web)
[![Sponsor](https://img.shields.io/badge/Sponsor-%E2%9D%A4-red?logo=github)](https://github.com/sponsors/claudioemmanuel)

Citizen auditing platform for Brazilian federal government data — public read, reproducible evidence.

OpenWatch ingests 23 open-government sources, resolves entities across datasets, and applies deterministic corruption-risk detectors to generate investigation-ready signals. Every signal carries numeric factors and links to the raw evidence that produced it.

> **Open-Core Model**
> This repository (`openwatch-br/openwatch`) is the **public OSS layer** — MIT license.
> The private analytics core (typologies T01–T28, entity resolution, pipelines) lives in
> [`openwatch-br/openwatch-core`](https://github.com/openwatch-br/openwatch-core) under BSL 1.1.

## Em Português

O OpenWatch é uma plataforma de auditoria cidadã para dados públicos federais do Brasil.
O sistema ingere múltiplas bases abertas, cruza entidades por CNPJ/CPF, detecta padrões
de risco por regras determinísticas e apresenta evidências reproduzíveis no portal web.

A camada de pontuação não depende de modelo generativo. IA generativa é opcional e usada
apenas para explicações em linguagem natural — nunca para calcular risco.

---

## What Lives Here (MIT)

| Component | Path | Purpose |
|-----------|------|---------|
| Web portal | `apps/web/` | Next.js public investigation interface |
| Public API | `apps/api/app/routers/public.py` | Read-only filtered endpoints |
| API gateway | `apps/api/` | FastAPI app, middleware, migrations |
| Config | `packages/config/` | Settings and environment management |
| Utilities | `packages/utils/` | Shared Python helpers |
| Public models | `packages/models/` | Output schemas, public response types |
| Public connectors | `packages/connectors/` (6 public) | ibge, pncp, portal_transparencia, compras_gov, comprasnet_contratos, brasilapi_cnpj |
| HTTP client | `packages/connectors/openwatch_connectors/http_client.py` | Generic async HTTP with rate limiting |
| TypeScript SDK | `packages/sdk/` | Client library for API consumers |
| UI components | `packages/ui/` | Reusable React components |
| Public tests | `tests/public/` | Tests for the public layer |
| Dev tooling | `Makefile`, `infra/docker/docker-compose.dev-lite.yml` | Local development |
| DB migrations | `apps/api/alembic/` | Public schema definition |

---

## Architecture

```
                      PUBLIC INTERNET
                            │
              ┌─────────────▼──────────────┐
              │  openwatch (this repo, MIT) │
              │  Next.js portal             │
              │  Public API (gateway only)  │
              └─────────────┬──────────────┘
                            │  HTTPS (internal service mesh)
              ┌─────────────▼──────────────────────────────────┐
              │  openwatch-core (private, BSL 1.1)              │
              │  Typologies T01–T28 · Entity Resolution         │
              │  Risk Analytics · Data Pipelines (Celery)       │
              │  Enrichment Connectors (20+)                    │
              └─────────────┬──────────────────────────────────┘
                            │
              ┌─────────────▼──────────────┐
              │  PostgreSQL 17 + pgvector   │
              │  Redis                      │
              └────────────────────────────┘
```

The public API is a **gateway only** — all computation runs in `openwatch-core` on
controlled infrastructure. See [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) for the full design.

---

## Quickstart (Local Development)

### Prerequisites

- Python 3.12+, [uv](https://docs.astral.sh/uv/), Node.js 20+, Docker Compose

### 1. Clone and install

```bash
git clone https://github.com/openwatch-br/openwatch.git
cd openwatch
uv sync --all-extras
cd apps/web && npm ci && cd ../..
```

### 2. Start infrastructure

```bash
make dev
# Starts PostgreSQL and Redis via Docker
```

### 3. Run migrations

```bash
make migrate
```

### 4. Start services

```bash
# API (with hot reload)
cd apps/api && uv run uvicorn app.main:app --reload --port 8000

# Web portal (separate terminal)
cd apps/web && NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

### 5. Open

- Portal: http://localhost:3000
- API docs: http://localhost:8000/docs (development only)

> **Note:** In local dev mode, the API uses a dual-mode adapter that can connect to the
> core service (set `CORE_SERVICE_URL`) or fall back to direct DB access when available.
> See `.env.example` for all configuration options.

---

## Data Sources (23 connectors)

| Source | Connector | License |
|--------|-----------|---------|
| Portal da Transparência (sanctions, spending) | `portal_transparencia` | Open (token required) |
| PNCP procurement | `pncp` | Open |
| Compras.gov.br | `compras_gov` | Open |
| ComprasNet contracts | `comprasnet_contratos` | Open |
| IBGE reference data | `ibge` | Open |
| BrasilAPI CNPJ (fallback) | `brasilapi_cnpj` | Open |
| + 17 enrichment connectors (TCU, TSE, TCE-*, Camara, Senado, BNDES, …) | `openwatch-core` | Open (data) |

The 6 connectors in the OSS layer are standalone wrappers for fully public government APIs.
The 17 enrichment connectors are in `openwatch-core` as part of the protected data strategy.

---

## Corruption Typologies

OpenWatch applies **28 deterministic typologies** (T01–T28) to detect corruption-risk patterns.
These algorithms are the core intellectual property of the project and reside in `openwatch-core`.

| Group | Examples |
|-------|---------|
| Procurement fraud | T01 supplier concentration, T03 contract splitting, T12 directed tender |
| Financial fraud | T05 price outlier, T04 amendment abuse, T23 BIM cost overrun |
| Cartels & networks | T07 cartel network, T19 bid rotation, T21 collusive cluster |
| Political & compliance | T22 political favoritism, T16 budget clientelism, T25 TCU condemned |

Full methodology: [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md)

---

## Contributing

We welcome contributions to the **public layer** — web portal, SDK, public connectors, utilities,
and documentation. See [CONTRIBUTING.md](./CONTRIBUTING.md) for the full guide.

Contributions to the typology engine, risk scoring, or entity resolution are managed internally
and are not accepted via public PRs.

---

## License

The code in this repository is released under the [MIT License](./LICENSE).

The `openwatch-core` repository is released under the
[Business Source License 1.1](./LICENSE-BSL) (BSL 1.1), which converts to Apache 2.0 after
four years from each file's commit date. Non-commercial research and civic journalism use
is always permitted.

---

## Security

Please report security vulnerabilities via [SECURITY.md](./SECURITY.md).
Do **not** open public issues for security findings.

---

## Sponsor

If OpenWatch helps your journalism, research, or civic tech work:
[**Become a sponsor**](https://github.com/sponsors/claudioemmanuel)
