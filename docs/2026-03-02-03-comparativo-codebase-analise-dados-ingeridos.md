# Comparativo Codebase x Analise Esperada (Dados Ingeridos -> Tipologias -> UI/UX)

Data de corte: **2026-03-02**  
Objetivo: comprovar, com evidencias tecnicas, se o app esta de fato:
1. ingerindo os dominios necessarios,
2. cruzando dados no motor,
3. aplicando tipologias esperadas,
4. exibindo isso com transparencia na interface.

## 1) Metodo de verificacao usado

## 1.1 Analise estatica de codigo
- conectores/jobs: `shared/connectors/*.py`
- tipologias e dominios requeridos: `shared/typologies/*.py`
- execucao de sinais: `worker/tasks/signal_tasks.py`
- status/cobertura no frontend: `web/src/components/ProcessingStatus.tsx`, `web/src/components/CoveragePanel.tsx`, `web/src/app/signal/[id]/page.tsx`

## 1.2 Verificacao de comportamento (testes)
Comando executado:
```bash
cd AuditorIA/auditoria-gov
uv run pytest tests/typologies/test_registry.py \
  tests/typologies/test_e2e_minimum_detectable.py \
  tests/worker/test_ingest_tasks.py \
  tests/worker/test_signal_tasks.py \
  tests/scheduler/test_schedule.py -q
```
Resultado:
- **40 passed** em 1.64s.

## 1.3 Verificacao operacional (Postgres real)
Consultas executadas em container `postgres` via `docker compose exec -T postgres psql ...` para:
- `raw_run` (ingestao),
- `event` (dados normalizados),
- `risk_signal` + `typology` (detecao),
- `coverage_registry` (estado de cobertura).

## 2) Evidencias principais (snapshot)

## 2.1 Ingestao (raw_run, ultimos 30 dias)
Sinais observados:
- alto volume ingerido em `despesa`, `contrato`, `transferencia` e `licitacao`.
- existencia de multiplos jobs com `status=error` e jobs `running` longos.

Exemplos do snapshot:
- `pncp_contracts`: 1 completed (37.000 fetched/normalized) + 6 error.
- `compras_licitacoes_by_period`: 1 completed (3.700/3.700) + 5 error.
- `pt_sancoes_ceis_cnep`: completed + running com alto `items_fetched` e `normalized=0` no run em andamento.

## 2.2 Dados normalizados (event)
`EVENT_30D`:
- `despesa`: 124.508
- `transferencia`: 52.610
- `contrato`: 40.700
- `licitacao`: 11.100
- `diario_oficial`: 6.780
- `sancao`: 15
- `emenda`: 15

Leitura tecnica:
- ha volume forte de eventos, mas com forte concentracao em poucos dominios.

## 2.3 Sinais gerados (risk_signal)
`RISK_30D`:
- `T03` critical/sufficient: 39
- `T03` high/sufficient: 21
- `T05` medium/insufficient: 1
- `T10` high/sufficient: 20

`RISK_LIFETIME`:
- apenas `T03`, `T05`, `T10` possuem sinais persistidos.

Leitura tecnica:
- embora existam 10 tipologias ativas no banco, a producao de sinais esta concentrada em 3 codigos.

## 2.4 Cobertura registrada
Na consulta direta, `coverage_registry` nao retornou linhas no snapshot analisado.

Impacto:
- o frontend consegue montar cobertura a partir do registry de conectores + latest runs, mas sem `coverage_registry` persistido perde-se parte da auditoria historica/frescor consolidado.

## 3) Mapeamento objetivo: dominio ingerido x tipologia

Levantamento por codigo (ConnectorRegistry + `enabled_in_mvp_incremental` + required_domains):
- jobs totais: **27**
- jobs incrementais habilitados: **15**
- dominios totais em conectores: **13**
- dominios habilitados no incremental: **7**
- dominios requeridos por tipologias: **6**

`DOMAIN_COVERAGE` (resumo):
- `contrato`: enabled ingest = true, tipologies = true
- `despesa`: true, true
- `licitacao`: true, true
- `sancao`: true, true
- `empresa`: false, true
- `remuneracao`: false, true
- `emenda`: true, false
- `transferencia`: true, false
- `diario_oficial`: true, false

Diagnostico chave:
- `empresa` e `remuneracao` sao necessarios para `T06`, `T09`, `T10`, mas nao estao habilitados no incremental de forma consistente.
- ha ingestao forte de `emenda`, `transferencia`, `diario_oficial` sem tipologias dedicadas no set atual.

## 4) Comparativo com os documentos legal-first e engineer-first

| Requisito | Evidencia de implementacao | Status |
|---|---|---|
| Exibir sinal como hipotese, nao condenacao | UX mostra severidade/confianca/completude; linguagem ainda depende de copy por pagina | Parcial |
| Cobrir todos os tipos/esferas discutidos | Tipologias atuais cobrem bem licitacao/contrato; faltam concussao, prevaricacao, clientelismo robusto, lavagem temporal | Parcial |
| Cruzar dados ingeridos com tipologias aplicaveis | Existe `required_domains`, mas nao ha painel canonico de aptidao/execucao por tipologia | Parcial |
| Rastreabilidade de evidencia | `evidence_refs`, `source_hash`, `completeness_score` implementados | Implementado |
| Transparencia de cobertura para usuario | Pagina de cobertura e status existem | Implementado |
| Transparencia de "tipologia executou ou nao" | Nao ha UX clara de execucao por tipologia+dominio+janela | Ausente |

## 5) Impacto direto em UI/UX (ponto critico)

Hoje o usuario ve sinais e cobertura, mas nao ve claramente:
- quais tipologias estavam aptas a rodar naquela janela,
- quais rodaram de fato,
- quais nao rodaram por falta de dominio/cobertura.

Consequencia de UX:
- risco de interpretar "ausencia de sinal" como "ausencia de risco", quando pode ser apenas falta de dado apto.

## 6) Backlog de melhoria para garantir confiabilidade do que aparece em tela

## P0 (imediato)
1. Criar metricas de execucao por tipologia-run (candidatos, emitidos, deduplicados, bloqueados por completude, bloqueados por dominio ausente).
2. Expor endpoint publico de "cobertura analitica" com matriz:
   - `tipologia`, `required_domains`, `domains_available`, `last_run_at`, `last_success_at`, `signals_30d`.
3. Adicionar card no Radar/Cobertura: **Confiabilidade da Analise**
   - % tipologias aptas
   - % tipologias executadas
   - dominios faltantes que bloqueiam tipologias
4. Habilitar/planejar ingestao incremental dos dominios que bloqueiam tipologias ativas (`empresa`, `remuneracao`) ou desativar temporariamente tipologias dependentes com aviso de indisponibilidade.

## P1
1. Implementar `T11`, `T12`, `T13` para cobrir lacunas legais/engenharia priorizadas.
2. Adicionar filtros no frontend por `sphere` e `corruption_type` (quando metadados forem adicionados).
3. Painel de funil por tipologia (entrada -> filtros -> sinais finais).

## P2
1. Tipologias processuais (`T14`, `T15`) dependentes de logs administrativos.
2. Lavagem por grafo temporal (`T16`) com series historicas de rede.
3. Metatipologia sistemica (`T18`) com recorrencia multi-orgao.

## 7) Criterios de aceite para "o que mostramos em tela"

O produto so deve declarar analise "confiavel" quando:
1. dominios requeridos pela tipologia estiverem disponiveis e atualizados;
2. tipologia tiver executado com sucesso na janela;
3. sinal tiver evidencias e completude acima do threshold;
4. UI mostrar explicitamente quando uma tipologia nao foi executada por falta de dado.

## 8) Conclusao executiva

- O motor atual ja tem fundamentos fortes (tipologias, completude, evidencias, dedup, UI de cobertura).
- O principal gap nao e apenas detectar mais: e **provar em tela que cada tipologia aplicavel realmente foi executada com os dados ingeridos**.
- A melhoria mais importante para backend + UI/UX e instituir uma camada de "cobertura analitica" por tipologia, conectando ingestao real, execucao real e exibicao confiavel para o usuario.
