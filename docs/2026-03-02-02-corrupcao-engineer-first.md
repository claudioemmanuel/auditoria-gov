# Deteccao de Corrupcao por Tipos e Esferas - Engineer First

Data de corte: **2026-03-02**  
Escopo: arquitetura de deteccao, contratos de dados, cobertura de tipologias e backlog tecnico para motor + produto.

## 1) Objetivo tecnico

Garantir que o sistema:
- cruze dados ingeridos de forma consistente,
- aplique tipologias de maneira auditavel,
- exponha confianca/completude real no frontend,
- permita evolucao segura para novas tipologias.

## 2) Fluxo tecnico de ponta a ponta

Pipeline alvo:
1. `ingest` (conectores/jobs por dominio)
2. `normalize` (schema canonico)
3. `entity resolution` (vinculos pessoa/empresa/orgao)
4. `baselines` (distribuicoes por contexto)
5. `signals` (tipologias)
6. `ai/explain` (explicacao)
7. `ui/api` (radar, sinal, cobertura, caso)

Arquivos-chave:
- conectores: [shared/connectors/__init__.py](/Users/claudioemmanuel/Documents/GitHub/AuditorIA/auditoria-gov/shared/connectors/__init__.py)
- contrato de job: [shared/connectors/base.py](/Users/claudioemmanuel/Documents/GitHub/AuditorIA/auditoria-gov/shared/connectors/base.py)
- tipologias: [shared/typologies/registry.py](/Users/claudioemmanuel/Documents/GitHub/AuditorIA/auditoria-gov/shared/typologies/registry.py)
- execucao de sinais: [worker/tasks/signal_tasks.py](/Users/claudioemmanuel/Documents/GitHub/AuditorIA/auditoria-gov/worker/tasks/signal_tasks.py)
- agenda: [shared/scheduler/schedule.py](/Users/claudioemmanuel/Documents/GitHub/AuditorIA/auditoria-gov/shared/scheduler/schedule.py)
- modelos: [shared/models/orm.py](/Users/claudioemmanuel/Documents/GitHub/AuditorIA/auditoria-gov/shared/models/orm.py), [shared/models/signals.py](/Users/claudioemmanuel/Documents/GitHub/AuditorIA/auditoria-gov/shared/models/signals.py)

## 3) Contrato minimo de dados para deteccao

Entidades-base:
- `Event`: fato canonico (tipo, data, fonte, valor, attrs)
- `Entity`: pessoa/empresa/orgao
- `EventParticipant`: papel da entidade no evento
- `RiskSignal`: saida persistida da tipologia

Campos criticos por dominio:
- `licitacao`: participantes, vencedor, modalidade, valor
- `contrato`: valor original, aditivos, vigencia
- `despesa`: pagamento/liquidacao/favorecido
- `sancao`: inicio/fim/tipo/alvo
- `empresa`: CNPJ, QSA, CNAE, abertura
- `remuneracao`: orgao, total, rubricas
- `emenda/transferencia`: origem, destino, valor, data

## 4) Score, severidade e gates de qualidade

Sinal final recomendado:
- `final_score = (w_rule*rule + w_anomaly*anomaly + w_network*network) * confidence`

Gates:
- sem evidencia suficiente => nao escalar para `high/critical`.
- severidade critica somente com evidencias independentes multiplas.

Ja implementado relevante:
- completude e rebaixamento de severidade em baixa completude: [worker/tasks/signal_tasks.py](/Users/claudioemmanuel/Documents/GitHub/AuditorIA/auditoria-gov/worker/tasks/signal_tasks.py)
- campos de completude/evidencia em `RiskSignalOut`: [shared/models/signals.py](/Users/claudioemmanuel/Documents/GitHub/AuditorIA/auditoria-gov/shared/models/signals.py)

## 5) Catalogo atual de tipologias (`T01`-`T10`)

| Codigo | Nome | Dominios |
|---|---|---|
| T01 | Concentracao em Fornecedor | licitacao |
| T02 | Baixa Competicao | licitacao |
| T03 | Fracionamento de Despesa | despesa, licitacao |
| T04 | Aditivo Outlier | contrato |
| T05 | Preco Outlier | licitacao, contrato |
| T06 | Proxy de Empresa de Fachada | licitacao, empresa |
| T07 | Rede de Cartel | licitacao |
| T08 | Sancao x Contrato | sancao, contrato |
| T09 | Proxy de Folha Fantasma | remuneracao |
| T10 | Terceirizacao Paralela | contrato, remuneracao |

Fonte: [shared/typologies](/Users/claudioemmanuel/Documents/GitHub/AuditorIA/auditoria-gov/shared/typologies)

## 6) Mapa tipo/esfera -> tipologia atual

Cobertura razoavel hoje:
- fraude licitatoria/sobrepreco/cartel: `T01,T02,T03,T04,T05,T07`
- sancao e contratacao indevida: `T08`
- peculato (proxy folha/terceirizacao): `T09,T10`

Cobertura parcial/ausente:
- corrupcao ativa/passiva (cadeia causal composta)
- concussao
- prevaricacao por SLA processual
- nepotismo/clientelismo relacional
- lavagem com grafo temporal

## 7) Backlog tecnico de tipologias novas

## P0
- `T11` Nepotismo e Conflito Relacional
- `T12` Sequencia de Favorecimento Contratual (composicao de sub-sinais)
- `T13` Clientelismo Orcamentario-Contratual

## P1
- `T14` Prevaricacao por SLA anomalo
- `T15` Concussao por bloqueio-liberacao
- `T16` Lavagem por camadas societarias/fluxo

## P2
- `T17` Captura Regulatoria / porta giratoria
- `T18` Recorrencia sistemica multi-orgao (metatipologia)

## 8) Contrato recomendado para novas tipologias

Sem quebrar `BaseTypology`, adicionar metadados por tipologia:
- `corruption_type`
- `sphere`
- `evidence_level`
- `data_dependencies`
- `false_positive_controls`

Objetivo:
- alinhar legal-first + engine + UX com semantica unificada.

## 9) Confiabilidade da analise exibida ao usuario (motor -> tela)

Frontend ja mostra:
- severidade/confianca/completude em detalhe de sinal: [web/src/app/signal/[id]/page.tsx](/Users/claudioemmanuel/Documents/GitHub/AuditorIA/auditoria-gov/web/src/app/signal/[id]/page.tsx)
- status de pipeline e cobertura: [web/src/components/ProcessingStatus.tsx](/Users/claudioemmanuel/Documents/GitHub/AuditorIA/auditoria-gov/web/src/components/ProcessingStatus.tsx), [web/src/components/CoveragePanel.tsx](/Users/claudioemmanuel/Documents/GitHub/AuditorIA/auditoria-gov/web/src/components/CoveragePanel.tsx)

Gap de UX/observabilidade:
- falta painel explicito "dominio ingerido X tipologia executada X ultimo sucesso" para evitar discrepancia entre o que existe no banco e o que aparece no radar.

## 10) Testes e verificacao tecnica

Suíte-chave de referencia:
- [tests/typologies/test_registry.py](/Users/claudioemmanuel/Documents/GitHub/AuditorIA/auditoria-gov/tests/typologies/test_registry.py)
- [tests/typologies/test_e2e_minimum_detectable.py](/Users/claudioemmanuel/Documents/GitHub/AuditorIA/auditoria-gov/tests/typologies/test_e2e_minimum_detectable.py)
- [tests/worker/test_ingest_tasks.py](/Users/claudioemmanuel/Documents/GitHub/AuditorIA/auditoria-gov/tests/worker/test_ingest_tasks.py)
- [tests/worker/test_signal_tasks.py](/Users/claudioemmanuel/Documents/GitHub/AuditorIA/auditoria-gov/tests/worker/test_signal_tasks.py)
- [tests/scheduler/test_schedule.py](/Users/claudioemmanuel/Documents/GitHub/AuditorIA/auditoria-gov/tests/scheduler/test_schedule.py)

## 11) Resultado esperado de engenharia

Em producao, deve ser possivel responder objetivamente:
1. quais dominios estao sendo ingeridos agora;
2. quais tipologias estao aptas a executar com esses dominios;
3. quais tipologias realmente executaram e geraram sinais;
4. qual parte disso e exibida de forma clara e honesta para o usuario final.

Esse fechamento e realizado no documento de comparativo da codebase.
