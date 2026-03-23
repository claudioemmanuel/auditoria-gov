# OpenWatch — Hardening Jurídico, Qualidade de ER e Renomeação da Plataforma

**Data:** 2026-03-23
**Status:** Aprovado para implementação
**Escopo:** Plataforma completa (backend, frontend, docs, identidade)
**Abordagem escolhida:** Hardening Jurídico Completo (Abordagem 2)

---

## 1. Contexto e Motivação

### 1.1 Renomeação: AuditorIA → OpenWatch

O nome **AuditorIA** foi concebido para sinalizar integração com Inteligência Artificial. Como essa integração não é o foco central da plataforma, o nome cria expectativa não correspondida. O novo nome **OpenWatch** reflete com precisão a missão real:

- **Open** → código aberto, dados abertos, acesso público irrestrito, sem login
- **Watch** → watchdog cidadão, monitoramento contínuo, vigilância sobre o gasto público

Funciona naturalmente em português e inglês. Tagline: *"Vigilância cidadã sobre o gasto público."*

| Artefato | Antes | Depois |
|----------|-------|--------|
| Repositório | `auditoria-gov` | `openwatch` |
| Nome público | AuditorIA Gov | OpenWatch |
| Domínio sugerido | — | `openwatch.com.br` |
| GitHub org | — | `openwatch-br` |
| Package Python | `auditoria_gov` | `openwatch` |
| Docker image prefix | `auditoria-gov-` | `openwatch-` |
| Variáveis de ambiente | `AUDITORIA_*` | `OPENWATCH_*` |

### 1.2 Postura estratégica

Plataforma **pública, sem autenticação**, acessível a qualquer cidadão. Todos os dados processados são públicos por obrigação legal (LAI, Lei 14.133/2021 Art. 174, CF/88 Art. 37). A plataforma não acusa — evidencia padrões estatísticos que merecem atenção.

Risco jurídico central identificado: **falso positivo na resolução de entidades (ER)** gerando associação indevida de uma entidade legítima a sinais de corrupção.

---

## 2. ER Confidence Shield

### 2.1 Problema

O ER produz `cluster_id` sem score associado. Um merge pode ocorrer por similaridade de nome sem identificador autoritativo em comum. Todas as entidades de um cluster herdam os sinais do cluster — incluindo potenciais falsos positivos.

### 2.2 Hierarquia de confiança por evidência

| Evidência | Score |
|-----------|-------|
| CNPJ exato idêntico | 100 (hard match) |
| CPF exato idêntico | 100 (hard match) |
| CNPJ matriz/filial + nome similar ≥ 90% | 95 |
| Nome idêntico normalizado + mesmo município | 85 |
| Nome similar ≥ 85% + co-participação em eventos | 75 |
| Nome similar ≥ 75% apenas | 55 |
| Abaixo de 60% | não merga (threshold mínimo) |

O `cluster_confidence` é o **mínimo** dos scores de todos os pares do cluster (elo mais fraco determina a confiança total).

### 2.3 Trilha de evidência do merge

Nova tabela `er_merge_evidence`:

```sql
entity_a_id      UUID NOT NULL REFERENCES entity(id),
entity_b_id      UUID NOT NULL REFERENCES entity(id),
confidence_score INTEGER NOT NULL CHECK (confidence_score BETWEEN 0 AND 100),
evidence_type    VARCHAR(50) NOT NULL,  -- cnpj_exact, cpf_exact, name_fuzzy, co_participation
evidence_detail  JSONB,
created_at       TIMESTAMPTZ DEFAULT NOW()
```

Permite explicar **por que** duas entidades foram fundidas — essencial para contestação pública.

### 2.4 Portão de visibilidade dos sinais

Todos os sinais são exibidos publicamente. O grau de confiança é comunicado via badge:

| cluster_confidence | Exibição |
|--------------------|----------|
| ≥ 80% | Sinal exibido normalmente, sem badge adicional |
| 60–79% | Badge âmbar `⚠️ Identidade com confiança parcial — verifique os dados de origem` |
| < 60% | Badge vermelho `🔴 Confiança insuficiente — dado disponível para análise, não para afirmação` |

Nenhum sinal é ocultado. A plataforma é transparente sobre incertezas em vez de filtrar informação.

### 2.5 Reavaliação incremental

Quando novas evidências chegam (ex.: CNPJ agora disponível), o merge é reavaliado automaticamente e o badge atualizado. Sinais anteriormente marcados com baixa confiança podem ser promovidos.

---

## 3. Score Composto de Confiança dos Sinais

### 3.1 Novo campo: `signal_confidence_score`

Cada `RiskSignal` recebe dois scores distintos:

- `severity_score` (existente): gravidade do padrão detectado
- `signal_confidence_score` (novo): qualidade/certeza dos dados que sustentam o sinal

### 3.2 Fórmula

```
signal_confidence = (
  er_confidence        × 0.40   # qualidade da identidade das entidades
  + data_freshness     × 0.25   # frescor dos dados de origem
  + source_coverage    × 0.20   # quantas fontes independentes confirmam
  + typology_evidence  × 0.15   # força das evidências numéricas da tipologia
)
```

| Componente | Cálculo |
|---|---|
| `er_confidence` | `cluster_confidence` do cluster das entidades envolvidas |
| `data_freshness` | dias desde o evento mais recente → decaimento logarítmico, máx 100 |
| `source_coverage` | conectores com evidência ÷ conectores relevantes para a tipologia |
| `typology_evidence` | score interno dos `factors` da tipologia, normalizado 0–100 |

### 3.3 Armazenamento

```sql
-- Novos campos em risk_signal:
signal_confidence_score  INTEGER CHECK (signal_confidence_score BETWEEN 0 AND 100),
confidence_factors       JSONB   -- breakdown: {er, freshness, coverage, evidence}
```

### 3.4 Exibição no frontend

```
Gravidade:   ████████░░  Alta (78/100)
Confiança:   ██████░░░░  Média (61/100)
```

Comunicação explícita: o sinal pode ser grave mas os dados que o sustentam podem ser parciais.

---

## 4. Transparência Metodológica

### 4.1 Página `/metodologia`

Conteúdo obrigatório:

| Bloco | Conteúdo |
|---|---|
| Missão | O que é OpenWatch, natureza informativa (não probatória) |
| Fontes | 11 fontes com link direto e data de última atualização |
| Como funciona a detecção | Explicação das tipologias em linguagem acessível |
| O que é um "sinal de risco" | Definição: padrão estatístico, não acusação |
| Graus de confiança | Tabela explicando badges âmbar/vermelho |
| Como reportar erro | Link para mecanismo de reporte |
| Base legal | CF/88 Art. 5° XXXIII, LAI 12.527/2011, Lei Anticorrupção 12.846/2013, LGPD Art. 7° II |

### 4.2 Página por tipologia `/tipologia/T03`

Cada tipologia tem página própria com:
- O que o detector procura (linguagem simples)
- Exemplo concreto de padrão detectado
- Threshold numérico com base legal
- Limitações conhecidas

Conteúdo extraído de `factor_metadata.py` — já existe, apenas precisa ser exposto publicamente.

### 4.3 Versionamento público

A página `/metodologia` exibe o commit hash atual do repositório com link para o histórico no GitHub. Toda alteração nas tipologias é auditável publicamente.

---

## 5. Mecanismo de Reporte de Erro + Disclaimers + Termos de Uso

### 5.1 Mecanismo de reporte ("Flag")

Formulário sem login acessível em cada card de sinal e perfil de entidade:

```
- Entidade ou sinal (pré-preenchido)
- Tipo: [ ] Entidade incorreta  [ ] Dado desatualizado  [ ] Outro
- Descrição (máx. 1000 chars)
- Fonte ou evidência contraditória (URL ou texto)
- E-mail para retorno (opcional)
```

Nova tabela `error_report`:

```sql
entity_id      UUID REFERENCES entity(id),
signal_id      UUID REFERENCES risk_signal(id),
report_type    VARCHAR(50),
description    TEXT,
evidence_url   TEXT,
contact_email  TEXT,
status         VARCHAR(20) DEFAULT 'pending',  -- pending / reviewing / resolved / dismissed
created_at     TIMESTAMPTZ DEFAULT NOW()
```

Se `status = resolved` e ER estava incorreto: trigger de reavaliação do cluster.

**Relevância jurídica:** A existência do canal demonstra boa-fé. Em processo judicial, a pergunta será *"o reclamante notificou a plataforma?"*. Se sim e a plataforma agiu, demonstrou diligência razoável.

### 5.2 Disclaimers contextuais

Em toda página de sinal:
> *"Este sinal é gerado automaticamente a partir de dados públicos e indica um padrão que merece atenção. Não constitui acusação, prova de ilicitude ou decisão administrativa. Confiança: [score]."*

Em toda página de entidade:
> *"Os dados exibidos são obtidos de fontes públicas oficiais. A associação entre registros de diferentes fontes é feita por algoritmo e pode conter imprecisões. [Reportar erro]"*

### 5.3 Termos de uso (`/termos`)

Cláusulas essenciais:
- Plataforma informativa, não probatória
- Usuário não pode usar dados para fins difamatórios, persecutórios ou de coação
- Plataforma age com diligência razoável; não garante precisão absoluta
- Reporte de erros disponível e analisado
- Dados públicos; reprodução permitida com atribuição
- Jurisdição: Brasil

---

## 6. Base Legal LGPD Formalizada

### 6.1 Substituição de "legítimo interesse" por base específica

Conforme Guia Orientativo ANPD 2024, plataformas que processam dados de portais de transparência devem usar **Art. 7°, II (cumprimento de obrigação legal)** ancorado na LAI, não legítimo interesse.

| Fonte | Base LGPD primária | Ancoragem |
|-------|-------------------|-----------|
| Portal da Transparência | Art. 7°, II | LAI Art. 8° §1° III |
| PNCP | Art. 7°, II | Lei 14.133/2021 Art. 174 |
| ComprasNet / Compras.gov | Art. 7°, II | Lei 14.133/2021 Art. 174 |
| TransfereGov | Art. 7°, II | Lei 13.019/2014 Art. 59 + LAI |
| Câmara / Senado | Art. 7°, §3° | CF Art. 37 + STF RE 652.777 |
| TSE | Art. 7°, §3° | Lei 9.504/1997 + Res. TSE 23.607 |
| Receita Federal CNPJ | Art. 7°, §3° | Lei 8.934/1994 |
| Querido Diário | Art. 7°, II | LAI Art. 8° |

### 6.2 Dados de pessoas físicas

Adicionar ao `COMPLIANCE.md`:

> **Dados de agentes públicos:** OpenWatch processa dados de servidores e agentes públicos exclusivamente no exercício de cargos e funções públicas. Conforme STF RE 652.777 e ANPD, esses dados têm publicidade garantida constitucionalmente. CPFs nunca são exibidos — apenas hashed internamente para cruzamento de registros.

### 6.3 Linguagem dos sinais pós-Lei 14.230/2021

A reforma da Lei de Improbidade (Lei 14.230/2021) exige **dolo específico** provado para responsabilização individual. Os textos dos sinais devem distinguir explicitamente:

- *"Padrão detectado sugere possível irregularidade sistêmica"* (sem implicar intenção)
- *"Investigação adicional recomendada para determinar responsabilidade individual"*

---

## 7. Auditoria das Tipologias vs. Leis Vigentes

### 7.1 Status de conformidade

| Tip. | Status | Problema |
|------|--------|---------|
| T01 | ✅ Conforme | — |
| T02 | ⚠️ Ajuste | Não trata "Diálogo Competitivo" (Art. 32, V — baixa competição legal por design) |
| T03 | ⚠️ Threshold | Usa Decreto 12.343/2024; migrar para Decreto 12.807/2025 (vigente 01/01/2026) |
| T04 | ✅ Conforme | — |
| T05 | ✅ Conforme | — |
| T06 | ✅ Conforme | — |
| T07 | ✅ Conforme | — |
| T08 | ✅ Conforme | — |
| T09 | ✅ Conforme | — |
| T10 | ✅ Conforme | — |
| T11 | ✅ Conforme | — |
| T12 | ⚠️ Ajuste | PMI (Procedimento de Manifestação de Interesse) não tratado como atenuante |
| T13 | ⚠️ Citação | Falta Lei 12.813/2013 (Lei de Conflito de Interesses) + Decreto 10.889/2022 |
| T14 | ✅ Conforme | — |
| T15 | ⚠️ Ajuste | Hipóteses de inexigibilidade baseadas na Lei 8.666/93; atualizar para Art. 74 Lei 14.133/2021 |
| T16 | 🔴 Crítico | RP-9 declarado inconstitucional (STF ADPFs 850/851/854, dez/2022); Emendas Pix com novos requisitos STF 2024 |
| T17 | ⚠️ Citação | Falta CP Art. 337-F como crime antecedente; COAF Res. 36/2021 |
| T18 | ✅ Conforme | — |
| T19 | ✅ Conforme | — |
| T20 | ✅ Conforme | — |
| T21 | ✅ Conforme | — |
| T22 | ✅ Conforme | — |

### 7.2 Correções prioritárias

**🔴 T16 — Reescrita crítica**

Modelar três regimes distintos:

```python
# emenda_type: individual | bancada | relator_rp9 | especial_pix | comissao

# Grupo 1 — RP-9 inconstitucional
if emenda_type == "relator_rp9" and occurred_at > date(2022, 12, 19):
    severity = HIGH; cite ADPF 850

# Grupo 2 — Emendas Pix sem rastreabilidade (requisitos STF 2024)
factors:
  - plano_trabalho_registered == False   → fator obrigatório
  - beneficiario_final_identificado == False → gap de transparência
  - conta_dedicada == False              → violação de condicionante

# Grupo 3 — Concentração (qualquer tipo)
HHI emendas por município > p90 → fator existente mantido
Janela temporal: ≤ 90 dias antes/após eleição → fator temporal

# Scoring (Nota Conjunta TCU/AGU/CGU/MGI nº 1/2025)
t16_severity = risco_constitucional×0.40 + materialidade_valor×0.35 + relevancia_temporal×0.25
```

**🔴 T03 — Externalizar thresholds**

```python
# Criar tabela dispensa_thresholds:
# (categoria, valor_brl, valid_from, valid_to, decreto_ref)
# Detector consulta threshold vigente na data do evento, não no momento de execução
# Decreto 12.807/2025 vigente desde 01/01/2026
```

**🟡 T02** — Adicionar: `if modalidade == "dialogo_competitivo": skip`

**🟡 T12** — Adicionar: se `pmi_realizado == True`, peso do fator "requisito restritivo" × 0.5

**🟡 T15** — Atualizar rol de inexigibilidades para Art. 74 Lei 14.133/2021 (credenciamento, Art. 79; notória especialização, Art. 74, III; etc.)

**🟢 T13** — Adicionar citações: Lei 12.813/2013 Art. 5°–6°; Decreto 10.889/2022

**🟢 T17** — Adicionar: CP Art. 337-F como crime antecedente; COAF Res. 36/2021; nota de dual exposure

---

## 8. Emendas Parlamentares: Framework Pós-RP-9

### 8.1 Tipagem dos eventos `emenda`

Atualizar conector `transferegov` para mapear `emenda_type`:

```
individual | bancada | relator_rp9 | especial_pix | comissao
```

### 8.2 Novo dado: `plano_trabalho_registered`

Desde janeiro 2025, o campo é obrigatório na plataforma Transferegov (requisito STF Min. Dino 2024). Atualizar conector para ingeri-lo.

### 8.3 Critérios de priorização (Nota Conjunta TCU/AGU/CGU/MGI nº 1/2025)

Incorporar os três critérios da nota como fatores do score de T16:
- **Risco constitucional** (RP-9 ou violação de condicionantes STF)
- **Materialidade** (valor absoluto vs. receita do município beneficiário)
- **Relevância temporal** (proximidade eleitoral)

---

## 9. Novas Tipologias

### T23 — Superfaturamento em Contratos com BIM Obrigatório

**Base legal:** Lei 14.133/2021 + Decreto 10.306/2020 (BIM obrigatório para obras federais > R$ 1,5M a partir de 2024).

**Padrão:**
```
contrato_obra com valor > R$ 1,5M (regime BIM)
+ variação de preço unitário por item > 2× mediana de baseline
+ aditivos de quantidade > 15% do valor original
→ indicador de manipulação de planilha BIM
```

**Diferença de T11:** T11 detecta manipulação pós-contrato. T23 detecta superfaturamento no projeto original.

**Dados necessários:** Eventos `contrato_obra` com atributo `valor_unitario_itens` (disponível via PNCP pós-jan/2024).

### T24 — Fraude em Cota ME/EPP

**Base legal:** LC 123/2006 + Lei 14.133/2021 Art. 4° + Decreto 8.538/2015.

**Padrão:**
```
entidade classificada como ME/EPP
+ data_abertura_cnpj < 180 dias antes da licitação
+ sócio(s) com participação em empresas médio/grande porte
  vencedoras no mesmo órgão nos últimos 2 anos
+ capital_social < R$ 10.000
→ proxy de empresa de fachada para captura de cota
```

**Dados necessários:** `data_abertura_cnpj`, `porte_empresa`, `socios` do conector Receita Federal CNPJ (já ingerido).

---

## 10. Documento de Auditoria das Tipologias

Criar `docs/typology-audit-14133.md` com mapeamento completo de cada tipologia contra Lei 14.133/2021, Lei 14.230/2021 e demais leis vigentes, indicando:

- Status: `✅ compatível` | `⚠️ threshold desatualizado` | `🔴 lógica incorreta` | `➕ lacuna`
- Mudança necessária e justificativa legal com artigo específico

---

## 11. Prioridades de Implementação

| Prioridade | Item | Esforço estimado |
|-----------|------|-----------------|
| 🔴 Crítica | Renomear plataforma para OpenWatch | 1–2 dias (sed global + configs) |
| 🔴 Crítica | Reescrever T16 (RP-9 + Emendas Pix) | 3–5 dias |
| 🔴 Crítica | Externalizar thresholds T03 + Decreto 12.807/2025 | 2 dias |
| 🔴 Crítica | ER Confidence Shield (tabela + scores + badges) | 5–7 dias |
| 🟡 Alta | Signal Confidence Score (campo + fórmula + UI) | 3–4 dias |
| 🟡 Alta | Mecanismo de reporte de erro (tabela + formulário + API) | 3–4 dias |
| 🟡 Alta | Página /metodologia + /tipologia/:code | 3–4 dias |
| 🟡 Alta | Correções T02, T12, T15 | 1–2 dias |
| 🟡 Alta | Atualizar COMPLIANCE.md (bases LGPD + linguagem sinais) | 1 dia |
| 🟢 Média | Termos de uso + disclaimers contextuais | 1–2 dias |
| 🟢 Média | Citações T13, T17 | 0.5 dia |
| 🟢 Média | Tipologia T24 (fraude ME/EPP) | 3–4 dias |
| 🟢 Média | Tipologia T23 (BIM) | 4–5 dias |
| 🟢 Média | Conector TransfereGov: ingerir `plano_trabalho_registered` | 1 dia |
| 🔵 Baixa | docs/typology-audit-14133.md | 1 dia |

---

## 12. Referências Legais

- CF/88 Arts. 5° XXXIII, 37, 74, 166
- Lei 14.133/2021 — Nova Lei de Licitações (Arts. 32, 74, 75, 79, 125, 156, 174, 337-E ao 337-P CP)
- Decreto 12.807/2025 — Thresholds 2026
- Lei 14.230/2021 — Reforma da Improbidade Administrativa
- STF Tema 1.199 (ARE 843.989) — dolo específico
- Lei 12.846/2013 — Lei Anticorrupção
- Lei 9.613/1998 (emenda Lei 12.683/2012) — Lavagem de Dinheiro
- Lei 12.813/2013 — Conflito de Interesses
- Lei 13.303/2016 — Lei das Estatais
- Lei 8.112/1990 Art. 118 — Acúmulo de Cargos
- LGPD — Lei 13.709/2018 Arts. 7°, 11, 18, 23
- LAI — Lei 12.527/2011 Art. 8°
- ANPD Guia Orientativo sobre Legítimo Interesse (2024)
- ANPD Guia Tratamento de Dados pelo Poder Público (2024)
- STF ADPFs 850/851/854/1014 — Orçamento Secreto RP-9 inconstitucional
- Nota Conjunta TCU/AGU/CGU/MGI nº 1/2025 — Emendas Pix
- TCU Acórdão 788/2025 — PNTP 2025
- TCU TC 009.980/2024-5 — LGPD organizações federais
- STF RE 652.777 — Dados de servidores públicos
- LC 123/2006 + Decreto 8.538/2015 — ME/EPP
- Decreto 10.306/2020 — BIM em obras públicas
- COAF Resolução nº 36/2021
