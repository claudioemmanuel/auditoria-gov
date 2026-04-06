# OpenWatch (Public Layer)

**Citizen auditing of Brazilian federal data.**

OpenWatch is an open-core platform that ingests public procurement, contracting, and financial data from Brazilian federal government sources, detects corruption-risk signals using a typology engine, and exposes results through a public API and web portal.

---

## Overview

This repository contains the **public-facing layer** of OpenWatch:

- **Frontend**: Next.js 15 portal for citizens, journalists, and researchers (`apps/web/`)
- **Public API**: FastAPI gateway that proxies analytical queries to the private analytics engine (`api/`)
- **Shared Packages**: Python utilities, config, and public-facing models (`packages/`, `shared/`)

> **Note:** The private analytics engine lives in [openwatch-core](https://github.com/openwatch-br/openwatch-core) (`BSL 1.1`). This repo is MIT-licensed and contains no protected analytics code.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  openwatch  (public, MIT)                        │
│  ┌───────────────┐   ┌────────────────────────────┐ │
│  │  Next.js    │   │  FastAPI public gateway   │ │
│  │  (Vercel)   │──▶│  api/                     │ │
│  └───────────────┘   └───────────────┬────────────┘ │
└──────────────────────────────┬───────────────┘
                               │ CORE_SERVICE_URL   │
                               ▼                    │
┌───────────────────────────────────────────────────┐
│  openwatch-core  (private, BSL 1.1)              │
│  Analytics · ER · Typologies · Workers · Infra   │
└───────────────────────────────────────────────────┘
```

---

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.12+ and [uv](https://docs.astral.sh/uv/)
- Node.js 20+ and [pnpm](https://pnpm.io/)

### 1. Clone and configure

```bash
git clone https://github.com/openwatch-br/openwatch.git
cd openwatch
cp .env.example .env
# Edit .env — set DATABASE_URL, REDIS_URL, and CORE_SERVICE_URL
```

### 2. Install dependencies

```bash
make sync
```

### 3. Start infrastructure

```bash
# Lightweight mode (Postgres + Redis only, run API/web natively)
make dev

# Full stack in Docker
make dev-full
```

### 4. Run database migrations

```bash
make migrate
```

### 5. Start the API and frontend

```bash
# API (split mode — requires openwatch-core running at CORE_SERVICE_URL)
uv run uvicorn api.app.main:app --reload --port 8000

# Frontend
cd apps/web && NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

---

## Local Development with `openwatch-core`

The public API delegates all analytical queries to `openwatch-core`. For full local development:

1. Clone and start [openwatch-core](https://github.com/openwatch-br/openwatch-core) on port 8001.
2. In this repo's `.env`, set:
   ```
   CORE_SERVICE_URL=http://localhost:8001
   CORE_API_KEY=<your-dev-key>
   ```
3. The public API will proxy all `/public/*` requests to core.

---

## Development Commands

| Command         | Description                                 |
|-----------------|---------------------------------------------|
| `make sync`     | Install Python and Node dependencies        |
| `make dev`      | Start Postgres + Redis in Docker            |
| `make dev-full` | Start full public stack in Docker           |
| `make migrate`  | Run Alembic DB migrations                   |
| `make test`     | Run public test suite                       |
| `make lint`     | Lint Python and TypeScript                  |
| `make typecheck`| Type-check Python and TypeScript            |
| `make boundaries`| Enforce import boundary rules              |

---

## Data Sources

OpenWatch ingests data from the following Brazilian government APIs:

- **Portal da Transparência** — federal contracts, procurement
- **Compras.gov** — procurement notices (PNCP)
- **DataJud/CNJ** — judicial records
- **CNPJ/Receita Federal** — corporate registration
- **TSE** — electoral campaign finance
- **Querido Diário** — municipal official gazettes
- *(additional sources in openwatch-core)*

---

## License

`MIT` — see [LICENSE](LICENSE).

The private analytics engine (`openwatch-core`) is licensed under `BSL 1.1` and converts to `Apache 2.0` after the change date.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
Security issues: see [SECURITY.md](SECURITY.md).
