# Data Sources

## Source Inventory

| Source | Access | Connector |
|---|---|---|
| Portal da Transparencia (sancoes + despesas + emendas + transferencias) | Token | `portal_transparencia` |
| PNCP | Public | `pncp` |
| Compras.gov.br | Public | `compras_gov` |
| ComprasNet contratos | Public | `comprasnet_contratos` |
| TransfereGov | Public | `transferegov` |
| Camara dos Deputados | Public | `camara` |
| Senado Federal | Public | `senado` |
| TSE eleitoral | Public bulk | `tse` |
| Receita Federal CNPJ | Public bulk | `receita_cnpj` |
| Querido Diario | Public | `querido_diario` |

Together these connectors provide 11 public-source streams used by the platform.

## Notes

- Portal da Transparencia requires `PORTAL_TRANSPARENCIA_TOKEN`
- TSE and Receita CNPJ connectors depend on local data directories due file size
- All connectors must implement deterministic `fetch` and `normalize` behavior
