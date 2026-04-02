# Data Sources

## Source Inventory

| Source | Access | Connector | Domain |
|---|---|---|---|
| Portal da Transparencia (sancoes + despesas + emendas + transferencias) | Token | `portal_transparencia` | Transparency |
| PNCP | Public | `pncp` | Procurement |
| Compras.gov.br | Public | `compras_gov` | Procurement |
| ComprasNet contratos | Public | `comprasnet_contratos` | Procurement |
| TransfereGov | Public | `transferegov` | Transfers |
| Camara dos Deputados | Public | `camara` | Legislative |
| Senado Federal | Public | `senado` | Legislative |
| TSE eleitoral | Public bulk | `tse` | Electoral |
| Receita Federal CNPJ | Public bulk | `receita_cnpj` | Corporate |
| Orcamento BIM (arquivo controlado) | File-backed deterministic | `orcamento_bim` | Budget |
| Querido Diario | Public | `querido_diario` | Gazette |
| TCU (Tribunal de Contas da Uniao) | Public | `tcu` | Audit |
| DataJud/CNJ | Public | `datajud` | Judiciary |
| IBGE | Public | `ibge` | Reference |
| TCE-RJ (Tribunal de Contas do Estado do RJ) | Public | `tce_rj` | State Audit |
| TCE-SP (Tribunal de Contas do Estado de SP) | Public | `tce_sp` | State Audit |
| Jurisprudencia (STF) | Public | `jurisprudencia` | Judiciary |
| Bacen (Banco Central) | Public | `bacen` | Economy |
| BNDES | Public | `bndes` | Financing |

Together these connectors provide 19 source streams with 70+ ingestion jobs.

## New Sources (MCP Brasil Integration)

Sources added via analysis of the [mcp-brasil](https://github.com/jxnxts/mcp-brasil) project:

| Source | APIs | Coverage | Cross-Reference Value |
|---|---|---|---|
| **TCE-RJ** | Licitações, contratos, penalidades municipais RJ | State (RJ) | Penalties × active contracts (T26) |
| **TCE-SP** | Despesas/receitas de 645 municípios paulistas | State (SP) | Municipal spending patterns |
| **Jurisprudência** | STF acórdãos sobre licitação e improbidade | National | Court rulings × active contracts (T28) |
| **Bacen** | Selic, IPCA, câmbio (enrichment-only) | National | Inflation-adjusted contract values |
| **BNDES** | Operações de financiamento (auto + não-auto) | National | Loan recipients × procurement winners (T27) |

## Notes

- Portal da Transparencia requires `PORTAL_TRANSPARENCIA_TOKEN`
- TSE and Receita CNPJ connectors depend on local data directories due file size
- Orcamento BIM reads JSONL from `ORCAMENTO_BIM_DATA_FILE` (default `/data/orcamento_bim/items.jsonl`)
- TCE-RJ domain (`dados.tcerj.tc.br`) has an approved DomainException (max_veracity: 0.90)
- Bacen connector is classified as ENRICHMENT_ONLY (never generates signals independently)
- All connectors must implement deterministic `fetch` and `normalize` behavior
