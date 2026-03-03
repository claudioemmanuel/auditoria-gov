# Backend: Complexidade Logaritmica e Roadmap de Performance

Data: 2026-03-02
Escopo: `auditoria-gov` (API + workers + filas + banco)

## 1) Objetivo desta doc

Definir, de forma objetiva e acionavel, como reduzir custo computacional do backend e aumentar throughput dos workers/jobs/queues.

Foco principal:
- sair de caminhos `O(n)`/`O(n^2)` em queries e upserts criticos
- mover hot paths para `O(log n)` usando indices corretos e batch upsert
- reduzir tempo de ingestao/normalizacao/ER/sinais com paralelismo controlado
- melhorar previsibilidade operacional (latencia, backlog e custo por execucao)

## 2) O que significa "complexidade logaritmica" no nosso backend

Em backend de dados, `O(log n)` normalmente vem de:
- busca por indice B-Tree (`WHERE chave = valor`)
- range scan com indice (`WHERE data >= ...`)
- lookup por chave unica (`UNIQUE INDEX`)

Em termos praticos:
- sem indice: PostgreSQL tende a `Seq Scan` (`O(n)`)
- com indice correto: `Index Scan/Bitmap Index Scan` (aprox. `O(log n)` para lookup)

Regra de ouro para este projeto:
- toda query executada em loop de worker precisa de caminho indexado
- toda operacao de deduplicacao/upsert precisa de chave unica materializada no banco

## 3) Diagnostico objetivo (estado atual)

### 3.1 Arquitetura de execucao

Hoje:
- um unico processo worker consome todas as filas (`ingest,normalize,er,signals,ai,default`) em `docker-compose.yml`
- roteamento de tasks por fila existe em `worker/worker_app.py`, mas sem isolamento por tipo de carga
- agendamento em `shared/scheduler/schedule.py` executa pipeline em horario fixo

Impacto:
- competicao por CPU/RAM entre tarefas heterogeneas
- tarefas longas podem aumentar latencia de tarefas curtas
- tuning fino por fila fica limitado

### 3.2 Modelagem e indices

Arquivos base:
- `shared/models/orm.py`
- `shared/repo/upsert_sync.py`

Pontos criticos observados:
- `Event` nao possui indice/unique em `(source_connector, source_id)` (lookup de upsert vira scan)
- `RawSource` nao possui indice em `(run_id, normalized)` e `(connector, job)` (normalizacao/cobertura escalam mal)
- `EventParticipant` nao possui unique em `(event_id, entity_id, role)` e nao tem indice focado em `(event_id, role)`
- `Entity` possui indice para `identifiers->>'cnpj'`, mas nao para `cpf` e `cpf_hash`
- fallback por `Entity(type, name_normalized)` nao possui indice composto
- `RawRun` sem indice composto para monitoria operacional (`connector, job, status, finished_at`)

### 3.3 Caminhos com custo alto

#### Ingest (`worker/tasks/ingest_tasks.py`)
- loop pagina a pagina
- insercao item a item em `RawSource`
- commits frequentes durante loop
- retry para qualquer excecao (`self.retry`), sem separar erro transiente vs nao transiente

Complexidade dominante:
- insert: `O(items)` (ok), porem com overhead alto por roundtrip
- monitoria/lookup sem indice adequado vira `O(n)` no crescimento

#### Normalize (`worker/tasks/normalize_tasks.py` + `shared/repo/upsert_sync.py`)
- `upsert_event_sync`: `SELECT ... WHERE source_connector + source_id` sem unique/index dedicado
- `upsert_participant_sync`: `SELECT` por `(event_id, entity_id, role)` sem unique/index dedicado
- upsert row-by-row com `flush` frequente

Complexidade dominante:
- hoje, na pratica, varios trechos aproximam `O(n)` por lookup; dentro de loops, custo efetivo tende a `O(n*m)`

#### Entity Resolution (`worker/tasks/er_tasks.py`)
- matching melhorou com blocking (nao full `O(n^2)` global), bom passo
- porem carga de participantes e edges ainda em massa
- upsert de edge verifica existencia edge a edge (`SELECT` por edge)

Complexidade dominante:
- matching: `O(n + sum(bucket_i^2))`
- upsert de edges: pode degradar para `O(e * custo_lookup)` sem chave unica/index composto

#### Coverage (`worker/tasks/coverage_tasks.py`)
- para cada `connector/job`, faz `COUNT(*)` em `RawSource` por filtro
- sem indice em `(connector, job)`, custo cresce com tabela inteira

Complexidade dominante:
- `O(jobs * n_raw_source)` no pior caso sem indice

#### Sinais de risco (`worker/tasks/signal_tasks.py` + `shared/typologies/*.py`)
- varias tipologias fazem filtros por `Event.type`, janelas de tempo e `EventParticipant.role`
- sem indices corretos para combinacoes mais usadas, consultas podem degradar

Complexidade dominante:
- tende a `O(n)` por tipologia quando plano cai para scan

### 3.4 Configuracao operacional

- `APP_ENV=development` com `echo=True` nos engines (`shared/db.py`, `shared/db_sync.py`)
- pools por processo podem sobrecarregar conexoes quando aumentar paralelismo
- nao ha tuning explicito de prefetch/time limits/result ttl por tipo de task

## 4) Mapa de complexidade: Hoje vs Alvo

| Etapa | Hoje (dominante) | Alvo | Alavanca principal |
|---|---|---|---|
| Upsert de evento | `O(n)` por lookup sem indice dedicado | `O(log n)` | `UNIQUE INDEX(source_connector, source_id)` + upsert nativo |
| Upsert de participante | `O(n)` por lookup em loop | `O(log n)` | unique + indice composto `(event_id, entity_id, role)` |
| Carregar pendentes de normalizacao | `O(n)` scan em `raw_source` | `O(log n + k)` | indice `(run_id, normalized)` |
| Cobertura por fonte/job | `O(n)` por contagem | `O(log n)` lookup + agregacao incremental | indice `(connector, job)` + tabela de metricas incrementais |
| ER edge upsert | ate `O(e*n)` | `O(e log n)` | unique de edge + batch `ON CONFLICT` |
| Tipologias por role/tipo | scans grandes | lookup/range indexado | indices por `event.type`, `event.occurred_at`, `event_participant.role` |

## 5) Roadmap completo (performance + reducao de complexidade)

## Fase 0 - Baseline e observabilidade (1-2 dias)

Objetivo:
- medir antes de otimizar

Acoes:
- habilitar metricas por task: `duration_ms`, `rows_read`, `rows_written`, `retry_count`
- coletar backlog por fila e `queue latency`
- habilitar `pg_stat_statements` e dashboard das top queries
- registrar p50/p95/p99 por task (`ingest`, `normalize`, `er`, `signals`, `ai`, `coverage`)

Criterio de aceite:
- dashboard unico com baseline tecnico antes da fase 1

## Fase 1 - Indices e constraints para O(log n) (2-4 dias)

Objetivo:
- transformar lookups criticos em caminhos indexados

Acoes SQL (migracao):

```sql
-- Event upsert key
CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS uq_event_source
ON event (source_connector, source_id);

-- RawSource hot paths
CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_raw_source_run_normalized
ON raw_source (run_id, normalized);

CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_raw_source_connector_job
ON raw_source (connector, job);

-- EventParticipant hot paths
CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS uq_event_participant_triplet
ON event_participant (event_id, entity_id, role);

CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_event_participant_event_role
ON event_participant (event_id, role);

CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_event_participant_role_entity
ON event_participant (role, entity_id);

-- Entity matching hot paths
CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_entity_identifiers_cpf
ON entity ((identifiers->>'cpf'));

CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_entity_identifiers_cpf_hash
ON entity ((identifiers->>'cpf_hash'));

CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_entity_type_name_norm
ON entity (type, name_normalized);

-- Operational monitoring
CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_raw_run_connector_job_status_finished
ON raw_run (connector, job, status, finished_at DESC);

-- Typology filtering
CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_event_type_occurred_at_id
ON event (type, occurred_at, id);
```

Validacoes obrigatorias antes do unique:
```sql
SELECT source_connector, source_id, COUNT(*)
FROM event
GROUP BY 1,2
HAVING COUNT(*) > 1;

SELECT event_id, entity_id, role, COUNT(*)
FROM event_participant
GROUP BY 1,2,3
HAVING COUNT(*) > 1;
```

Criterio de aceite:
- principais queries saem de `Seq Scan` para `Index Scan/Bitmap Index Scan`
- queda minima de 50% no p95 de normalize/cobertura em base de teste representativa

## Fase 2 - Batch upsert e menos roundtrip (3-5 dias)

Objetivo:
- reduzir custo por item processado

Acoes:
- ingest: trocar insert item-a-item por batch insert (`insert(...).values([...])`) com commit por lote
- normalize: trocar `select+flush` repetitivo por `INSERT ... ON CONFLICT DO UPDATE` em lote
- separar lotes (`chunk_size`) para evitar pico de memoria
- reduzir flush/commit desnecessario em loops internos

Criterio de aceite:
- throughput de ingest (itens/s) +2x em carga comparavel
- tempo medio por 1000 registros reduzido >=40%

## Fase 3 - Topologia de filas/workers por perfil de carga (2-3 dias)

Objetivo:
- eliminar competicao entre tarefas de natureza diferente

Acoes:
- separar workers por fila:
  - worker-ingest
  - worker-normalize
  - worker-er
  - worker-signals
  - worker-ai
  - worker-default
- ajustar `concurrency` por perfil:
  - I/O bound (`ingest`, `ai`): maior paralelismo controlado
  - CPU/DB bound (`normalize`, `er`, `signals`): moderado
- configurar:
  - `worker_prefetch_multiplier` por fila
  - `task_acks_late=true` para tarefas longas
  - `task_reject_on_worker_lost=true`
  - `result_expires` e `task_ignore_result` onde aplicavel

Criterio de aceite:
- p95 de fila curta (ex: `coverage`) nao degradar durante janelas de ingest pesada
- backlog maximo por fila dentro de limite definido

## Fase 4 - ER e grafo em modo incremental + batch (4-7 dias)

Objetivo:
- evitar rerun caro em massa

Acoes:
- ER incremental por "entidades alteradas desde ultimo ciclo"
- manter watermark por fonte/job para ER
- edge upsert em lote com `ON CONFLICT` usando chave composta (from,to,type)
- limitar escopo de participantes por janela temporal e/ou run_id

Criterio de aceite:
- runtime do ER escala por delta e nao por volume historico total
- custo de edge upsert proporcional ao numero de edges novas

## Fase 5 - Tipologias e aplicacao de sinais com custo previsivel (3-6 dias)

Objetivo:
- garantir que tipologias rodem em dados ingeridos sem custo explosivo

Acoes:
- padronizar consultas tipologicas para usar filtros indexados (`event.type`, janela tempo, `role`)
- adicionar modo "dry-run explicativo" por tipologia:
  - quantos eventos candidatos
  - quantos passaram em cada regra
  - quantos sinais gerados
- armazenar auditoria de execucao por tipologia (`run_id`, contadores por etapa)
- deduplicar sinais por janela/chave de negocio quando aplicavel

Criterio de aceite:
- cada tipologia reporta funil completo de aplicacao
- zero caixa-preta para "porque nao gerou sinal"

## Fase 6 - Operacao continua e hardening (2-4 dias)

Objetivo:
- estabilidade de longo prazo

Acoes:
- revisar tamanho dos pools de conexao por processo
- desabilitar SQL echo em ambientes de carga
- politicas de retry apenas para erros transientes (timeout/5xx/429)
- dead-letter strategy para falhas recorrentes
- rotina de manutencao de resultados antigos do Celery

Criterio de aceite:
- queda sustentada de erro/retry inutil
- uso de CPU/memoria/conexoes dentro de SLO

## 6) Checklist de verificacao de completude do motor

## Pipeline de processamento (workers/jobs)
- [ ] Cada job possui trilha: ingest -> normalize -> ER (quando aplicavel) -> signals -> AI
- [ ] Cada execucao gera metadados auditaveis (`inicio`, `fim`, `itens`, `erro`, `versao`) 
- [ ] Reprocessamento idempotente validado para runs repetidas

## Tipologias de risco
- [ ] Toda tipologia registra funil de execucao (candidatos, filtrados, sinais)
- [ ] Regras com thresholds possuem parametros versionados
- [ ] Cobertura por dominio atende `required_domains` de cada tipologia

## Resolucao de entidades + grafo + IA
- [ ] ER com metricas de match deterministico/probabilistico por ciclo
- [ ] Grafo com edges deduplicadas e pesos consistentes
- [ ] IA roda apenas onde agrega valor (prioridade alta/critica) e com trilha de evidencia

## Transparencia para usuario final
- [ ] Link de detalhes por job de sucesso com amostra legivel
- [ ] Campos complexos renderizados como tabela/estrutura, nao JSON cru no card principal
- [ ] Origem e periodo dos dados exibidos com clareza

## 7) KPIs e metas (SLO tecnico)

KPIs obrigatorios:
- throughput de ingest (`items/s`) por connector/job
- p95/p99 de `normalize_run`, `run_entity_resolution`, `run_single_signal`
- queue latency p95 por fila
- taxa de retry util vs inutil
- percentual de queries com seq scan nos hot paths

Metas iniciais (30 dias):
- reduzir p95 de normalize >= 50%
- reduzir custo de cobertura >= 70% (tempo total da task)
- zerar hot-path sem indice dedicado
- manter backlog critico < 1 ciclo de agenda

## 8) Plano 30-60-90 dias

30 dias:
- Fases 0, 1 e parte da 2 concluidas
- ganhos rapidos de indice + batch insert

60 dias:
- Fases 2 e 3 concluidas
- isolamento de filas/workers e tuning de concorrencia

90 dias:
- Fases 4, 5 e 6 concluidas
- motor com execucao explicavel, incremental e com custo previsivel

## 9) Ordem recomendada de execucao (pragmatica)

1. Indices + constraints (Fase 1)
2. Batch upsert em ingest/normalize (Fase 2)
3. Separacao de workers por fila (Fase 3)
4. ER incremental + edge upsert em lote (Fase 4)
5. Funil explicativo de tipologias (Fase 5)
6. Hardening operacional (Fase 6)

Sem esta ordem, qualquer ajuste de concorrencia tende a mascarar gargalo estrutural de banco.

## 10) Entregavel esperado apos aplicar roadmap

Backend com:
- hot paths predominantemente `O(log n)` em lookup/upsert
- processamento em lote e menor roundtrip por registro
- workers isolados por perfil de carga
- pipeline audivel ponta-a-ponta
- tipologias explicaveis em "como/onde/quando/por que" para cada sinal
