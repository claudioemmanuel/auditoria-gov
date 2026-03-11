# AuditorIA Gov

[![CI](https://github.com/claudioemmanuel/auditoria-gov/actions/workflows/ci.yml/badge.svg)](https://github.com/claudioemmanuel/auditoria-gov/actions/workflows/ci.yml)
[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL--3.0-blue.svg)](./LICENSE)
[![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)](./pyproject.toml)
[![Docker Compose](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](./docker-compose.yml)

Citizen auditing platform for Brazilian federal government data.

AuditorIA Gov ingests public datasets from procurement, spending, legislative, electoral, and corporate registries, resolves entities across sources, and applies deterministic corruption-risk typologies to generate reproducible investigation signals. The interface is public-read only and each signal links to concrete evidence.

The scoring and detection layer is deterministic (statistics + graph analysis). Optional LLM support is used only for narrative explanations, not for risk scoring.

## Em Português (resumo)

O AuditorIA Gov é uma plataforma de auditoria cidadã para dados públicos federais do Brasil. O sistema ingere múltiplas bases abertas, cruza entidades, detecta sinais de risco de corrupção por regras determinísticas e mostra evidências reproduzíveis no portal web.

A camada analítica não depende de modelo generativo para pontuação. IA generativa é opcional e usada apenas para explicações em linguagem natural.

## Architecture Overview

```text
                             +----------------------+
                             |   Next.js (web/)     |
                             | Public investigation |
                             +----------+-----------+
                                        |
                                        v
+-------------------+       +-----------+-----------+       +-----------------------+
| Celery Beat       |-----> | FastAPI (api/)        | <---- | Redis (cache/broker)  |
| scheduler         |       | Public + internal API |       +-----------------------+
+---------+---------+       +-----------+-----------+
          |                             |
          v                             v
+---------+---------+       +-----------+-----------+
| Celery Worker     |-----> | PostgreSQL 17 +       |
| ingest/ER/signals |       | pgvector              |
+---------+---------+       +-----------+-----------+
          |
          v
+-------------------+
| 11 public sources |
| connectors/jobs   |
+-------------------+
```

See [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) for the public architecture/design document.

## Data Sources (11)

| # | Source | Connector / Jobs | Access |
|---|--------|-------------------|--------|
| 1 | Portal da Transparência - sanctions (CEIS/CNEP) | `portal_transparencia` / `pt_sancoes_ceis_cnep` | Token required |
| 2 | Portal da Transparência - spending/transfers | `portal_transparencia` / `pt_*` expense, travel, card, benefits, amendments, transfers | Token required |
| 3 | PNCP | `pncp` / `pncp_contracting_notices`, `pncp_contracts`, `pncp_arp` | Public |
| 4 | Compras.gov.br | `compras_gov` / licitações + CATMAT/CATSER catalogs | Public |
| 5 | ComprasNet contracts | `comprasnet_contratos` / `cnet_contracts` | Public |
| 6 | TransfereGov | `transferegov` / convenio and transfer jobs | Public |
| 7 | Câmara dos Deputados | `camara` / deputies, quota expenses, organs | Public |
| 8 | Senado Federal | `senado` / senators, CEAPS expenses | Public |
| 9 | TSE electoral data | `tse` / candidates, assets, campaign revenues, campaign expenses | Public (bulk downloads) |
| 10 | Receita Federal CNPJ | `receita_cnpj` / companies, partners, establishments | Public (bulk downloads) |
| 11 | Querido Diario gazettes | `querido_diario` / municipal gazette entries | Public |

## Corruption Typologies (Deterministic Detectors)

| Code | Detector | Primary Pattern |
|------|----------|-----------------|
| T01 | Supplier concentration | Recurring concentration in a small supplier set |
| T02 | Low competition | Procurement records with low bidder competition |
| T03 | Expense splitting | Sequential expenses that indicate threshold splitting |
| T04 | Amendment outlier | Outlier behavior in parliamentary amendment spending |
| T05 | Price outlier | Item-level price anomalies vs. baseline references |
| T06 | Shell company proxy | Corporate profile and behavior consistent with shell proxies |
| T07 | Cartel network | Recurrent co-participation and network collusion indicators |
| T08 | Sanctions mismatch | Contracting activity involving sanctioned entities |
| T09 | Ghost payroll proxy | Payroll-like inconsistencies and proxy ghost-worker patterns |
| T10 | Outsourcing + parallel payroll | Outsourcing contracts overlapping suspicious payroll patterns |
| T11 | Spreadsheet manipulation (jogo de planilha) | Unit price inflation exploited via contract amendments in engineering works |
| T12 | Directed tender (edital direcionado) | Tender requirements tailored to a pre-selected supplier |
| T13 | Conflict of interest | Contracting agent has financial or family ties to the winning supplier |
| T14 | Compound favoritism sequence | Persistent accumulation of multiple favoritism signals for the same supplier |
| T15 | False sole-source (inexigibilidade indevida) | Sole-source procurement where qualified alternatives exist |
| T16 | Budget clientelism (emenda pix) | Parliamentary transfers without work plan or disproportionate to recipient capacity |
| T17 | Layered money laundering | Circular fund flows between interconnected entities post-contract |
| T18 | Illegal position accumulation | Simultaneous public roles or dismissed officials active in contracting companies |
| T19 | Bid rotation | Alternância sistemática de vencedores em licitações repetidas — indicador de cartel coordenado |
| T20 | Phantom bidders | Empresas participantes sem histórico operacional real — proxy para concorrência simulada |
| T21 | Collusive cluster | Cluster de fornecedores com comportamento de lances estatisticamente coordenados |
| T22 | Political favoritism | Correlação temporal entre contribuições eleitorais e contratos públicos |

## Quick Start

### 1. Clone

```bash
git clone https://github.com/claudioemmanuel/auditoria-gov.git
cd auditoria-gov
```

### 2. Configure environment

```bash
cp .env.example .env
# fill PORTAL_TRANSPARENCIA_TOKEN and CPF_HASH_SALT
```

### 3. Start services

```bash
docker compose up --build
```

### 4. Run migrations

```bash
docker compose run --rm api alembic -c api/alembic.ini upgrade head
```

### 5. Trigger ingestion and pipeline

```bash
curl -X POST http://localhost:8000/internal/ingest/all
curl -X POST http://localhost:8000/internal/er/run
curl -X POST http://localhost:8000/internal/baselines/run
curl -X POST http://localhost:8000/internal/signals/run
curl -X POST http://localhost:8000/internal/coverage/update
```

### 6. Open interfaces

- Web: http://localhost:3000
- API docs (Swagger): http://localhost:8000/docs

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | Async SQLAlchemy PostgreSQL DSN | Yes |
| `DATABASE_URL_SYNC` | Sync PostgreSQL DSN for sync tasks/utilities | Yes |
| `POSTGRES_USER` | PostgreSQL container user | Docker local |
| `POSTGRES_PASSWORD` | PostgreSQL container password | Docker local |
| `POSTGRES_DB` | PostgreSQL container database name | Docker local |
| `REDIS_URL` | Redis URL for cache and app services | Yes |
| `PORTAL_TRANSPARENCIA_TOKEN` | API token for CGU Portal da Transparência | Yes (for `pt_*` jobs) |
| `TSE_DATA_DIR` | Local directory for TSE bulk files | Optional |
| `RECEITA_CNPJ_DATA_DIR` | Local directory for Receita CNPJ bulk files | Optional |
| `LLM_PROVIDER` | `none` (default) or `openai` | Optional |
| `OPENAI_API_KEY` | OpenAI API key when `LLM_PROVIDER=openai` | Conditional |
| `OPENAI_MODEL` | OpenAI chat model for explanations | Optional |
| `EMBEDDING_MODEL` | Embedding model for retrieval/explanations | Optional |
| `RATE_LIMIT_PORTAL_TRANSPARENCIA_RPS` | Outgoing RPS cap for Portal da Transparência | Optional |
| `RATE_LIMIT_COMPRAS_GOV_RPS` | Outgoing RPS cap for Compras.gov | Optional |
| `RATE_LIMIT_PNCP_RPS` | Outgoing RPS cap for PNCP | Optional |
| `RATE_LIMIT_DEFAULT_RPS` | Default outgoing RPS cap for connectors | Optional |
| `PUBLIC_RATE_LIMIT_RPS` | Public API incoming rate limit | Optional |
| `PUBLIC_RATE_LIMIT_BURST` | Public API burst limit | Optional |
| `CACHE_TTL_SECONDS` | Public endpoint cache TTL | Optional |
| `CELERY_BROKER_URL` | Celery broker URL | Yes |
| `CELERY_RESULT_BACKEND` | Celery result backend URL | Yes |
| `CPF_HASH_SALT` | Salt used to hash CPF values (LGPD control) | Yes (production) |
| `APP_ENV` | `development`, `staging`, or `production` | Yes |
| `LOG_LEVEL` | Application logging level | Optional |

See [`.env.example`](./.env.example) for defaults.

## Running Tests

Backend:

```bash
uv sync --extra test
uv run --extra test pytest -q
```

Frontend checks:

```bash
cd web
npm ci
npm run lint
npm run build
```

## Compliance & Respaldo Legal

[![LAI Compliant](https://img.shields.io/badge/LAI-Lei%2012.527%2F2011-green)](https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2011/lei/l12527.htm)
[![LGPD Compliant](https://img.shields.io/badge/LGPD-Lei%2013.709%2F2018-blue)](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm)
[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL--3.0-blue.svg)](./LICENSE)
[![Dados Públicos](https://img.shields.io/badge/Dados-Transparência%20Ativa%20Obrigatória-orange)](./docs/COMPLIANCE.md)

A plataforma opera inteiramente sobre **dados já tornados públicos por força de lei** — nenhum dado é obtido por acesso não autorizado ou violação de sigilo.

| Pilar | Garantia |
|-------|---------|
| **Tecnologicamente robusto** | Whitelist de domínios `.gov.br`/`.leg.br`, testes automatizados, código aberto AGPL-3.0, cadeia de proveniência auditável |
| **Metodologicamente defensável** | Tipologias com base legal explícita, scoring determinístico, veracity registry público via `GET /public/sources` |
| **Juridicamente responsável** | CF/88 art. 5º XXXIII, LAI (Lei 12.527/2011), LGPD art. 7º VI, Lei Anticorrupção 12.846/2013 |
| **Publicamente auditável** | Open source, endpoints de proveniência públicos, metodologia documentada, aviso de disclaimer em cada sinal |

Ver documento técnico-jurídico completo: [docs/COMPLIANCE.md](./docs/COMPLIANCE.md)

## Contributing

Contributions are welcome.
Read [CONTRIBUTING.md](./CONTRIBUTING.md) before opening issues or pull requests.

## Wiki

Project wiki pages are versioned in [docs/wiki](./docs/wiki/README.md) and intended for GitHub Wiki publication.

## License

Licensed under the GNU Affero General Public License v3.0.
See [LICENSE](./LICENSE).

## Acknowledgments

- Brazilian federal open data providers: CGU Portal da Transparência, PNCP, Compras.gov.br, TransfereGov, Câmara dos Deputados, Senado Federal, TSE, Receita Federal
- Querido Diario project for public gazette access
- Core open-source ecosystem: FastAPI, Celery, PostgreSQL, SQLAlchemy, Next.js, React, and many other OSS libraries
