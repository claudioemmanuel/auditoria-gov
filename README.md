# AuditorIA Gov

Plataforma de auditoria pública de dados do governo federal brasileiro.
Ingere dados abertos, resolve entidades, detecta indicadores de corrupção e apresenta evidências reproduzíveis com explicações em linguagem natural.

---

## Visão Geral

AuditorIA Gov conecta **11 fontes de dados públicas federais** (Executivo +
Legislativo), cruza entidades, e aplica **10 tipologias de corrupção** para
gerar sinais de risco auditáveis pelo cidadão.

Todo o processamento analítico é **determinístico** — pontuação e sinais não
dependem de IA. O LLM (OpenAI) é opcional e usado apenas para sumários
explicativos.

---

## Arquitetura

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│    Next.js 15    │────▶│    FastAPI        │────▶│  PostgreSQL 17   │
│    (web/)        │     │    (api/)         │     │  + pgvector      │
└──────────────────┘     └────────┬─────────┘     └──────────────────┘
                                  │                         ▲
                         ┌────────▼─────────┐               │
                         │  Celery + Beat   │───────────────┘
                         │  (worker/)       │
                         └────────┬─────────┘
                                  │
                         ┌────────▼─────────┐
                         │     Redis 7      │
                         └──────────────────┘
```

| Camada | Tecnologia |
|--------|-----------|
| Banco de dados | PostgreSQL 17 + pgvector |
| Cache / Broker | Redis 7 |
| API | FastAPI + Uvicorn |
| Worker | Celery + Beat |
| Frontend | Next.js 15 · React 19 · Tailwind v4 · shadcn/ui |
| ORM | SQLAlchemy 2 (async) |
| Migrações | Alembic |
| LLM | OpenAI (opcional — fallback determinístico por padrão) |
| Runtime Python | uv |

---

## Fontes de Dados

| Conector | Fonte | Autenticação |
|----------|-------|-------------|
| `portal_transparencia` | Portal da Transparência (8 jobs) | Token obrigatório |
| `pncp` | PNCP — Contratações Públicas | Pública |
| `compras_gov` | Compras.gov.br | Pública |
| `comprasnet_contratos` | ComprasNet / PNCP fallback | Pública |
| `transferegov` | TransfereGov (convênios) | Pública |
| `camara` | Câmara dos Deputados | Pública |
| `senado` | Senado Federal / Codante | Pública |
| `querido_diario` | Diários Oficiais municipais | Pública |
| `tse` | TSE — dados eleitorais (ZIP/CSV) | Pública |
| `receita_cnpj` | Receita Federal — CNPJ bulk | Pública |

Janela histórica padrão: **5 anos**. Os conectores TSE e Receita Federal fazem
download automático dos arquivos em `/data/tse` e `/data/receita_cnpj`
(idempotente — reutiliza arquivos já baixados).

---

## Tipologias de Corrupção

| Código | Nome |
|--------|------|
| T01 | Concentração de fornecedor |
| T02 | Baixa competitividade licitatória |
| T03 | Fracionamento de despesa |
| T04 | Emenda parlamentar outlier |
| T05 | Sobrepreço por item |
| T06 | Empresa de fachada (proxy) |
| T07 | Rede de cartel |
| T08 | Contratação de sancionado |
| T09 | Folha fantasma (proxy) |
| T10 | Terceirização com folha paralela |

---

## Quick Start

### Pré-requisitos

- Docker + Docker Compose
- Token do Portal da Transparência (obrigatório para jobs `pt_*`)

### 1. Configurar variáveis de ambiente

```bash
cp .env.example .env
# edite .env e preencha PORTAL_TRANSPARENCIA_TOKEN
```

Obtenha o token em:
- Cadastro: <https://portaldatransparencia.gov.br/api-de-dados/cadastrar-email>
- Gerenciar: <https://portaldatransparencia.gov.br/api-de-dados/gerenciar-chave>

### 2. Subir os serviços

```bash
docker compose up --build
```

| Serviço | Endereço |
|---------|---------|
| Frontend | <http://localhost:3000> |
| API (Swagger) | <http://localhost:8000/docs> |
| PostgreSQL | `localhost:5432` |
| Redis | `localhost:6379` |

### 3. Executar migrações

```bash
docker compose run --rm api alembic -c api/alembic.ini upgrade head
```

### 4. Disparar ingestão

```bash
# Todos os jobs habilitados
curl -X POST http://localhost:8000/internal/ingest/all

# Checar status
curl -s http://localhost:8000/internal/ingest/status | python3 -m json.tool
```

### 5. Processar pipeline analítico

Após a ingestão completar:

```bash
curl -X POST http://localhost:8000/internal/er/run          # entity resolution
curl -X POST http://localhost:8000/internal/baselines/run   # baselines de preço
curl -X POST http://localhost:8000/internal/signals/run     # geração de sinais
curl -X POST http://localhost:8000/internal/coverage/update # cobertura
```

---

## Estrutura do Projeto

```
auditoria-gov/
├── shared/                  # Núcleo compartilhado (api + worker)
│   ├── connectors/          # 10 conectores de fontes públicas
│   ├── typologies/          # 10 detectores de tipologias (T01–T10)
│   ├── er/                  # Entity resolution (clustering + matching)
│   ├── baselines/           # Cálculo de baseline de preços
│   ├── models/              # ORM (SQLAlchemy) + modelos canônicos
│   ├── repo/                # Camada de acesso ao banco
│   ├── ai/                  # Provedores LLM (opcional)
│   └── config.py            # Configurações via variáveis de ambiente
├── api/                     # FastAPI + Alembic
│   ├── app/routers/         # Rotas públicas + internas
│   └── alembic/             # Migrações de banco
├── worker/                  # Celery tasks + Beat scheduler
│   └── tasks/               # ingest, normalize, er, baselines, signals
├── web/                     # Frontend Next.js (PT-BR)
├── tests/                   # Suite de testes (pytest)
├── docs/                    # Documentação técnica e planos
├── infra/                   # Init SQL do PostgreSQL
└── docker-compose.yml
```

---

## Desenvolvimento Local (sem Docker)

```bash
# Instalar dependências Python com uv
uv sync

# Rodar testes
uv run pytest

# API local (requer PostgreSQL e Redis rodando)
uv run uvicorn api.app.main:app --reload
```

---

## Variáveis de Ambiente

Veja [`.env.example`](.env.example) para a lista completa.

Variáveis críticas:

| Variável | Descrição | Obrigatória |
|----------|-----------|-------------|
| `DATABASE_URL` | URL async do PostgreSQL | Sim |
| `REDIS_URL` | URL do Redis | Sim |
| `PORTAL_TRANSPARENCIA_TOKEN` | Token da API federal | Sim (jobs `pt_*`) |
| `CPF_HASH_SALT` | Salt para hash de CPFs (LGPD) | Sim (produção) |
| `LLM_PROVIDER` | `none` (padrão) ou `openai` | Não |
| `OPENAI_API_KEY` | Chave OpenAI (só se `LLM_PROVIDER=openai`) | Não |
| `TSE_DATA_DIR` | Diretório para CSVs do TSE (~600MB/ano) | Não |
| `RECEITA_CNPJ_DATA_DIR` | Diretório para bulk CNPJ (~6GB) | Não |

---

## Documentação de APIs

- **Swagger UI:** <http://localhost:8000/docs>
- **Chaves de API:** [`docs/api-keys.md`](docs/api-keys.md)
