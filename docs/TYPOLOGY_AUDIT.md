# Typology Audit — OpenWatch

**Versão:** 1.0
**Data:** 2026-03-23
**Escopo:** Auditoria técnico-jurídica de todas as 24 tipologias registradas
**Revisão:** A cada novo ciclo de dados ou mudança legislativa relevante

---

## Legenda

| Campo | Descrição |
|-------|-----------|
| **Código** | Identificador único da tipologia |
| **Nome** | Nome canônico em português |
| **Evidência** | `direct` = viola norma específica; `indirect` = anomalia estatística; `proxy` = indicador associado |
| **Domínios** | Event types necessários para execução |
| **Status** | `ativo` = dispara sinais reais; `stub` = código pronto, aguarda dados; `sem_dados` = dados não ingeridos |
| **Testes** | Arquivo de teste e cobertura |
| **Limitações** | Falsos positivos conhecidos / dependências de dados ausentes |

---

## T01 — Concentração em Fornecedor

| Item | Valor |
|------|-------|
| **Base Legal** | Lei 14.133/2021, Art. 9°, IV; Lei 12.529/2011 (CADE) |
| **Tipo de Corrupção** | fraude_licitatoria |
| **Evidência** | indirect |
| **Domínios** | `licitacao`, `contrato` |
| **Threshold** | HHI > 0.70 (concentração acima de 70% por orgao/categoria) |
| **Status** | ativo |
| **Testes** | `tests/typologies/test_t01*.py` |
| **Limitações** | Alta taxa de falso positivo em órgãos com poucos fornecedores no segmento. Sem dados de empresa/CNPJ ingeridos ainda. |

---

## T02 — Baixa Competição

| Item | Valor |
|------|-------|
| **Base Legal** | Lei 14.133/2021, Art. 337-F |
| **Tipo de Corrupção** | fraude_licitatoria |
| **Evidência** | indirect |
| **Domínios** | `licitacao` |
| **Threshold** | 0 participantes em modalidades não-competitivas (dispensa, inexigibilidade, diálogo competitivo, credenciamento, pré-qualificação) |
| **Status** | ativo (ruidoso) |
| **Testes** | `tests/typologies/test_t02*.py` |
| **Limitações** | Todas as 300 dispensa do PNCP atual têm 0 licitantes → 300 sinais por definição. Necessita filtro por modalidade para reduzir ruído em produção. |

---

## T03 — Fracionamento de Despesa

| Item | Valor |
|------|-------|
| **Base Legal** | Lei 14.133/2021, Art. 337-E; Lei 8.666/1993, Art. 24 |
| **Tipo de Corrupção** | fraude_licitatoria |
| **Evidência** | direct |
| **Domínios** | `licitacao`, `contrato` |
| **Threshold** | ≥ 2 compras ao mesmo fornecedor em ≤ 2 dias com soma > limite dispensa (fonte: tabela `dispensa_threshold`) |
| **Status** | ativo |
| **Testes** | `tests/typologies/test_t03_threshold.py` |
| **Limitações** | Thresholds externos dependem de dados na tabela `DispensaThreshold`. Decree 12.343/2024: R$ 62.725,59 (bens) / R$ 125.451,15 (obras). |

---

## T04 — Aditivo Outlier

| Item | Valor |
|------|-------|
| **Base Legal** | Lei 14.133/2021, Art. 337-K |
| **Tipo de Corrupção** | fraude_licitatoria, corrupcao_passiva |
| **Evidência** | indirect |
| **Domínios** | `contrato` |
| **Threshold** | Valor ou extensão fora de IQR × 1.5 para o tipo de contrato |
| **Status** | ativo |
| **Testes** | `tests/typologies/test_t04*.py` |
| **Limitações** | Dados de contrato 2021 sem amendment_count/modality attrs — aditivos mal populados. |

---

## T05 — Preço Outlier

| Item | Valor |
|------|-------|
| **Base Legal** | Lei 14.133/2021, Art. 337-F |
| **Tipo de Corrupção** | fraude_licitatoria |
| **Evidência** | indirect |
| **Domínios** | `licitacao`, `contrato` |
| **Threshold** | Desvio > 2σ da mediana por CATMAT/CATSER |
| **Status** | ativo |
| **Testes** | `tests/typologies/test_t05*.py` |
| **Limitações** | Sem histórico de preços CATMAT ingerido — baselines calculados sobre amostra 2021 pequena. |

---

## T06 — Proxy de Empresa de Fachada

| Item | Valor |
|------|-------|
| **Base Legal** | Lei 14.133/2021, Art. 14, III; Lei 8.934/94 |
| **Tipo de Corrupção** | fraude_licitatoria |
| **Evidência** | proxy |
| **Domínios** | `empresa` (Receita Federal) |
| **Threshold** | ≥ 2 indicadores proxy: capital < R$ 1.000, CNAE inconsistente, endereço compartilhado |
| **Status** | sem_dados |
| **Testes** | `tests/typologies/test_t06*.py` |
| **Limitações** | Depende de cobertura histórica da Receita CNPJ para maior recall; alias de compatibilidade `receita_federal_cnpj` → `receita_cnpj` ativo. |

---

## T07 — Rede de Cartel

| Item | Valor |
|------|-------|
| **Base Legal** | Lei 12.529/2011, Art. 36; Lei 14.133/2021, Art. 337-F |
| **Tipo de Corrupção** | fraude_licitatoria |
| **Evidência** | indirect |
| **Domínios** | `licitacao`, `contrato` |
| **Threshold** | Coeficiente de variação de lances < 5% entre empresas em ≥ 3 licitações comuns |
| **Status** | ativo |
| **Testes** | `tests/typologies/test_t07*.py` |
| **Limitações** | Dados 2021 com poucos licitantes por pregão — amostras pequenas para detecção de variância. |

---

## T08 — Sanção × Contrato

| Item | Valor |
|------|-------|
| **Base Legal** | Lei 14.133/2021, Art. 14, I-III; CEIS/CNEP/CEPIM |
| **Tipo de Corrupção** | fraude_licitatoria |
| **Evidência** | direct |
| **Domínios** | `sancao`, `contrato` |
| **Threshold** | Sanção ativa (sem sanction_end ou sanction_end > contract_date) + contrato ativo com mesmo CNPJ/CPF |
| **Status** | ativo |
| **Testes** | `tests/typologies/test_t08*.py` |
| **Limitações** | 9 entidades cruzadas em 2024+; contratos 2021 encerrados antes das sanções. execute_chunked_in aplicado para evitar crash asyncpg. |

---

## T09 — Proxy de Folha Fantasma

| Item | Valor |
|------|-------|
| **Base Legal** | Lei 8.429/1992, Art. 11; CP Art. 312 |
| **Tipo de Corrupção** | peculato |
| **Evidência** | proxy |
| **Domínios** | `remuneracao` (Portal da Transparência) |
| **Threshold** | Servidor com vínculo ativo sem remuneração no período ou remuneração R$ 0 |
| **Status** | sem_dados |
| **Testes** | `tests/typologies/test_t09*.py` |
| **Limitações** | Sensível à cobertura de folha por órgão/período; conector `pt_servidores_remuneracao` está ativo e exige ingestão contínua para evitar lacunas temporais. |

---

## T10 — Terceirização Paralela

| Item | Valor |
|------|-------|
| **Base Legal** | Lei 14.133/2021, Art. 48, §3°; Decreto 9.507/2018 |
| **Tipo de Corrupção** | fraude_licitatoria |
| **Evidência** | indirect |
| **Domínios** | `remuneracao`, `contrato` |
| **Threshold** | Mesmo CATSER contratado + servidor próprio com função equivalente no órgão |
| **Status** | sem_dados |
| **Testes** | `tests/typologies/test_t10*.py` |
| **Limitações** | Requer cruzamento de remuneração (não ingerido) com contratos de serviços. |

---

## T11 — Jogo de Planilha

| Item | Valor |
|------|-------|
| **Base Legal** | Lei 14.133/2021, Art. 337-K; Acórdão TCU 2.622/2013 |
| **Tipo de Corrupção** | fraude_licitatoria |
| **Evidência** | direct |
| **Domínios** | `contrato` |
| **Threshold** | Item com preço inflado + aumento de quantidade via aditivo subsequente em mesma obra |
| **Status** | ativo |
| **Testes** | `tests/typologies/test_t11*.py` |
| **Limitações** | Requer dados de planilha orçamentária por item (CATMAT/CATSER por linha). |

---

## T12 — Edital Direcionado

| Item | Valor |
|------|-------|
| **Base Legal** | Lei 14.133/2021, Art. 337-E; CF/88, Art. 37, XXI |
| **Tipo de Corrupção** | fraude_licitatoria |
| **Evidência** | indirect |
| **Domínios** | `licitacao` |
| **Threshold** | Restrictiveness score > 0.65; atenuado por 0.5 quando pmi_realizado=True (maioria) |
| **Status** | ativo |
| **Testes** | `tests/typologies/test_t12*.py` |
| **Limitações** | PMI atenuação implementada. Score baseado em attrs de edital; exige dados de PMI que podem não estar presentes. |

---

## T13 — Conflito de Interesses

| Item | Valor |
|------|-------|
| **Base Legal** | Decreto 7.203/2010; Lei 12.813/2013; Decreto 10.889/2022 |
| **Tipo de Corrupção** | nepotismo_clientelismo |
| **Evidência** | direct |
| **Domínios** | `contrato`, entidades (ER) |
| **Threshold** | Agente público com vínculo familiar/societário com fornecedor vencedor (cluster ER) |
| **Status** | ativo (wave 2) |
| **Testes** | `tests/typologies/test_t13*.py` |
| **Limitações** | Exige ER de alta qualidade. Falsos positivos possíveis em empresas com nomes comuns. |

---

## T14 — Sequência de Favorecimento Contratual

| Item | Valor |
|------|-------|
| **Base Legal** | Lei 14.133/2021, Art. 337-F; Lei 8.429/1992, Art. 10 |
| **Tipo de Corrupção** | fraude_licitatoria |
| **Evidência** | indirect |
| **Domínios** | `risk_signal` (meta: depende de wave 1+2) |
| **Threshold** | Entidade com ≥ 3 sinais de tipologias distintas (T01+T02+T03+T04+T05 etc.) na janela dinâmica resolvida |
| **Status** | ativo (wave 3) |
| **Testes** | `tests/typologies/test_t14*.py` |
| **Limitações** | Depende de sinais das ondas 1 e 2. A janela dinâmica usa piso/teto configuráveis e se ajusta ao histórico efetivamente disponível. |

---

## T15 — Inexigibilidade Indevida

| Item | Valor |
|------|-------|
| **Base Legal** | Lei 14.133/2021, Art. 74 (hipóteses válidas); Art. 337-F |
| **Tipo de Corrupção** | fraude_licitatoria |
| **Evidência** | direct |
| **Domínios** | `licitacao` |
| **Threshold** | Inexigibilidade com subtipo fora de {profissional_singular, credenciamento, notoria_especializacao, exclusividade, natureza_singular} |
| **Status** | ativo |
| **Testes** | `tests/typologies/test_t15*.py` |
| **Limitações** | Subtipo vem de `attrs.inexigibilidade_subtype`. Dados 2021 sem esse campo → dispara por ausência. |

---

## T16 — Clientelismo Orçamentário-Contratual

| Item | Valor |
|------|-------|
| **Base Legal** | CF/88 Art. 166-A + EC 105/2019 (Emendas Pix); ADI 7502 STF (RP-9, inconstitucional após 2022-12-19) |
| **Tipo de Corrupção** | nepotismo_clientelismo |
| **Evidência** | direct (GROUP 1 e 2), indirect (GROUP 3) |
| **Domínios** | `transferencia`, `emenda` |
| **Threshold** | GROUP 1: emenda_type=relator_rp9 após 19/12/2022 → HIGH; GROUP 2: Pix sem plano_trabalho ou beneficiario_final ou conta_dedicada → MEDIUM; GROUP 3: HHI > 0.7 em emendas por parlamentar |
| **Status** | ativo |
| **Testes** | `tests/typologies/test_t16_rp9_pix.py` |
| **Limitações** | GROUP 2: flags de transparência Pix dependem de attrs nos dados TransfereGov. GROUP 3 requer mais dados de emenda. |

---

## T17 — Lavagem via Camadas Societárias

| Item | Valor |
|------|-------|
| **Base Legal** | Lei 9.613/1998; CP Art. 337-F; COAF Resolução nº 36/2021 |
| **Tipo de Corrupção** | lavagem |
| **Evidência** | indirect |
| **Domínios** | `contrato`, entidades (ER) |
| **Threshold** | Fluxo circular: company A → B → C → A com contratos públicos intermediários |
| **Status** | ativo (wave 2) |
| **Testes** | `tests/typologies/test_t17*.py` |
| **Limitações** | Requer dados societários (Receita Federal) para detectar camadas. Sem CNPJ ingerido, detecção parcial via ER. |

---

## T18 — Acúmulo Ilegal de Cargos

| Item | Valor |
|------|-------|
| **Base Legal** | CF/88 Art. 37, XVI-XVII; Lei 8.112/90, Art. 117-118; Lei 8.429/1992 |
| **Tipo de Corrupção** | peculato, prevaricacao |
| **Evidência** | direct |
| **Domínios** | `remuneracao` |
| **Threshold** | Mesmo CPF com vínculo ativo em dois órgãos diferentes simultaneamente no mesmo período |
| **Status** | sem_dados |
| **Testes** | `tests/typologies/test_t18*.py` |
| **Limitações** | Requer boa cobertura de remuneração (`pt_servidores_remuneracao`) e metadados de período (`period_start`/`period_end`) para máxima precisão. |

---

## T19 — Rotação de Vencedores

| Item | Valor |
|------|-------|
| **Base Legal** | Lei 12.529/2011, Art. 36; Lei 14.133/2021, Art. 337-F |
| **Tipo de Corrupção** | fraude_licitatoria |
| **Evidência** | indirect |
| **Domínios** | `licitacao`, `contrato` |
| **Threshold** | Grupo de ≥ 3 empresas com alternância sistemática de vitórias (nenhuma perde mais de 2× seguidas) em mesmo segmento |
| **Status** | ativo |
| **Testes** | `tests/typologies/test_t19*.py` |
| **Limitações** | execute_chunked_in aplicado. Amostras 2021 pequenas para detecção de rotação. |

---

## T20 — Licitantes Fantasmas

| Item | Valor |
|------|-------|
| **Base Legal** | Lei 14.133/2021, Art. 337-F; CP Art. 347 |
| **Tipo de Corrupção** | fraude_licitatoria |
| **Evidência** | proxy |
| **Domínios** | `licitacao` |
| **Threshold** | Empresa vence com proposta abaixo de TODOS os concorrentes que depois desistem; ou empresa nunca vence exceto quando concorrentes são os mesmos |
| **Status** | ativo |
| **Testes** | `tests/typologies/test_t20*.py` |
| **Limitações** | execute_chunked_in aplicado. |

---

## T21 — Cluster Colusivo

| Item | Valor |
|------|-------|
| **Base Legal** | Lei 12.529/2011, Art. 36; Lei 14.133/2021, Art. 337-F |
| **Tipo de Corrupção** | fraude_licitatoria |
| **Evidência** | indirect |
| **Domínios** | `licitacao`, entidades (ER) |
| **Threshold** | Cluster de empresas com taxa de vitória conjunta > 70% nas mesmas licitações |
| **Status** | ativo |
| **Testes** | `tests/typologies/test_t21*.py` |
| **Limitações** | execute_chunked_in aplicado. Requer ER para identificar clusters. |

---

## T22 — Favorecimento Político

| Item | Valor |
|------|-------|
| **Base Legal** | Lei 9.504/1997, Art. 81-A; Lei 8.429/1992, Art. 9°, III; FATF Rec. 12 |
| **Tipo de Corrupção** | nepotismo_clientelismo, corrupcao_ativa_passiva |
| **Evidência** | indirect |
| **Domínios** | `doacao_eleitoral`, `contrato` |
| **Threshold** | ≥ 2 pares (doação → contrato) com intervalo ≤ 24 meses |
| **Status** | ativo |
| **Testes** | `tests/typologies/test_t22*.py` |
| **Limitações** | Qualidade depende da disponibilidade anual do TSE; mapeamento de papéis PT-BR/EN (`doador`/`donor`, `winner`/`supplier`) ativo para evitar perda de sinal. |

---

## T23 — Superfaturamento BIM

| Item | Valor |
|------|-------|
| **Base Legal** | Lei 14.133/2021, Art. 122, §3°; Decreto 9.983/2019; Lei 8.429/1992, Art. 9°, XI |
| **Tipo de Corrupção** | fraude_licitatoria, peculato |
| **Evidência** | direct |
| **Domínios** | `orcamento_bim` |
| **Threshold** | Preço unitário contratado > 20% acima do SINAPI por item; ≥ 3 itens por obra |
| **Status** | ativo |
| **Testes** | `tests/typologies/test_t23_bim_cost_overrun.py` |
| **Limitações** | Depende da qualidade do arquivo `orcamento_bim` e da cobertura por obra/itens SINAPI. Severidade: MEDIUM ≥20%, HIGH ≥40%, CRITICAL ≥80% desvio mediano. |

---

## T24 — Fraude em Cota ME/EPP

| Item | Valor |
|------|-------|
| **Base Legal** | LC 123/2006, Art. 47-49; Lei 14.133/2021, Art. 48; Decreto 8.538/2015; Lei 8.429/1992, Art. 11 |
| **Tipo de Corrupção** | fraude_licitatoria |
| **Evidência** | direct |
| **Domínios** | `licitacao` |
| **Threshold** | GROUP A: porte_empresa ∉ {ME,EPP,MEI} + evento me_epp_exclusive → CRITICAL; GROUP B: ≥ 3 cotas exclusivas no mesmo órgão em 12 meses → HIGH |
| **Status** | ativo |
| **Testes** | `tests/typologies/test_t24_me_epp_quota_fraud.py` |
| **Limitações** | Cobertura de `me_epp_exclusive` em PNCP histórico ainda é heterogênea; normalização adiciona `source_limitations` quando attrs críticos não existem no payload. |

---

## Resumo por Status

| Status | Tipologias | Quantidade |
|--------|-----------|------------|
| **ativo** | T01, T02, T03, T04, T05, T07, T08, T11, T12, T13, T14, T15, T16, T17, T18, T19, T20, T21, T22, T23, T24 | 21 |
| **sem_dados** | T06, T09, T10 | 3 |
| **stub** | — | 0 |

## Resumo por Evidência

| Nível | Tipologias |
|-------|-----------|
| **direct** | T03, T08, T11, T13, T15, T16 (G1/G2), T18, T23, T24 |
| **indirect** | T01, T02, T04, T05, T07, T12, T14, T16 (G3), T17, T19, T20, T21, T22 |
| **proxy** | T06, T09, T20 |

## Soluções Sistêmicas Implementadas (com risco residual)

1. **Histórico PNCP (pós-2021)**: o pipeline usa janela temporal dinâmica (piso/teto configuráveis) para reduzir distorção de baseline quando o histórico ainda é curto.  
   **Risco residual:** modalidades competitivas em 2021 seguem com baixa amostra.

2. **Conectores ausentes**: cobertura operacional para `receita_cnpj`, `pt_servidores_remuneracao`, `doacao_eleitoral` e `orcamento_bim` está ativa, incluindo compatibilidade `receita_federal_cnpj` → `receita_cnpj` e job legado `tse_doacoes`.  
   **Risco residual:** qualidade e periodicidade de ingestão por fonte.

3. **Atributos faltantes no PNCP 2021**: normalização passou a preencher/inferir `porte_empresa`, `me_epp_exclusive`, `inexigibilidade_subtype` e `pmi_realizado`, com `source_limitations` explícito quando o payload não permite completar o campo.  
   **Risco residual:** heterogeneidade histórica da origem.

4. **Janela temporal fixa**: removida em favor de resolução dinâmica por domínio com limites de segurança (`TYPOLOGY_WINDOW_MIN_DAYS` e `TYPOLOGY_WINDOW_MAX_DAYS`).  
   **Risco residual:** ingestão retroativa pré-2021 pode alterar baselines futuros, como esperado.

5. **Limite de parâmetros asyncpg**: `execute_chunked_in` foi reforçado com deduplicação determinística, tamanho de lote sensível ao orçamento de parâmetros e logs estruturados para rastreabilidade operacional.  
   **Risco residual:** consultas extremamente complexas ainda dependem de modelagem cuidadosa de filtros.

---

*Documento gerado em 2026-03-23. Atualizar a cada novo ciclo de dados ou alteração legislativa.*
