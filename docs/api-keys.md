# API Keys — OpenWatch

## Required

### Portal da Transparência (`PORTAL_TRANSPARENCIA_TOKEN`)

Required for all Portal da Transparência jobs:
- `pt_sancoes_ceis_cnep` — CEIS/CNEP sanctions
- `pt_servidores_remuneracao` — Federal payroll
- `pt_viagens` — Official travel
- `pt_cartao_pagamento` — Payment card transactions
- `pt_despesas_execucao` — Budget execution
- `pt_beneficios` — Social benefits by municipality
- `pt_emendas` — Parliamentary amendments
- `pt_convenios_transferencias` — Voluntary transfers

**Registration:**
1. Request token: https://portaldatransparencia.gov.br/api-de-dados/cadastrar-email
2. Manage token: https://portaldatransparencia.gov.br/api-de-dados/gerenciar-chave

**Rate limits:**
- Basic (default): 500 requests/day
- Perfil Prata/Gold (via Gov.br): 10,000 requests/day

```env
PORTAL_TRANSPARENCIA_TOKEN=your-token-here
```

---

## Optional

### OpenAI (`OPENAI_API_KEY`)

Required only for AI explanation features (typology summaries, risk narratives).
When `LLM_PROVIDER=none` (default), all analysis runs without AI — scores and
signals are deterministic.

**Registration:** https://platform.openai.com/api-keys

```env
OPENAI_API_KEY=your-key-here
LLM_PROVIDER=openai   # default: none
```

---

## No Authentication Required

All other connectors use public APIs or bulk downloads with no authentication:

| Connector | Source | Notes |
|-----------|--------|-------|
| `pncp` | PNCP — Portal Nacional de Contratações Públicas | Public REST API |
| `compras_gov` | Compras.gov.br open-data API | Public REST API |
| `comprasnet_contratos` | Compras.gov.br / PNCP fallback | Public REST API |
| `transferegov` | TransfereGov PostgREST API | Public REST API |
| `camara` | Câmara dos Deputados open-data API | Public REST API |
| `senado` | Senado Federal / Codante API | Public REST API |
| `querido_diario` | Querido Diário gazette API | Public REST API |
| `tse` | TSE CDN ZIP downloads | ~200MB per dataset, one-time |
| `receita_cnpj` | Receita Federal CNPJ bulk CSVs | ~6GB total, one-time download |

### Data directory requirements

TSE and Receita Federal connectors download large files on first run:

```env
TSE_DATA_DIR=/data/tse              # default — ~600MB per election year
RECEITA_CNPJ_DATA_DIR=/data/receita_cnpj  # default — ~6GB total
```

Ensure these paths have sufficient disk space and write permissions.
Downloads are idempotent — if the CSV already exists, the download is skipped.
