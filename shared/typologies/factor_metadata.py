"""Human-readable metadata for every factor key across all typologies.

Each entry maps a factor key (as stored in RiskSignal.factors) to:
- label: short PT-BR label shown in the UI
- description: explanatory text for auditors
- unit: type hint for formatting (brl, percent, days, count, boolean, number, ratio, score, text)
"""

FACTOR_METADATA: dict[str, dict[str, str]] = {
    # ── T10 - Terceirizacao Paralela ──────────────────────────────────
    "n_factors": {
        "label": "Fatores detectados",
        "description": "Quantidade de indicadores de risco presentes (de 4 possiveis)",
        "unit": "count",
    },
    "span_days": {
        "label": "Duracao total",
        "description": "Periodo em dias entre o primeiro e o ultimo contrato do par comprador-fornecedor",
        "unit": "days",
    },
    "n_contracts": {
        "label": "Contratos",
        "description": "Quantidade de contratos entre o mesmo comprador e fornecedor",
        "unit": "count",
    },
    "concentration": {
        "label": "Concentracao no fornecedor",
        "description": "Indica se 3 ou mais contratos foram firmados com o mesmo fornecedor (renovacoes sem competicao)",
        "unit": "boolean",
    },
    "long_duration": {
        "label": "Duracao prolongada",
        "description": "Indica se o relacionamento contratual ultrapassa 5 anos continuos",
        "unit": "boolean",
    },
    "total_value_brl": {
        "label": "Valor total",
        "description": "Soma dos valores de todos os contratos identificados entre comprador e fornecedor",
        "unit": "brl",
    },
    "outsourcing_flag": {
        "label": "Indicador de terceirizacao",
        "description": "Identifica se o objeto contratual contem termos tipicos de terceirizacao (limpeza, vigilancia, mao de obra, etc.)",
        "unit": "boolean",
    },
    "total_amendments": {
        "label": "Total de aditivos",
        "description": "Quantidade total de termos aditivos em todos os contratos do par",
        "unit": "count",
    },
    "amendment_pct": {
        "label": "Acrescimo por aditivos",
        "description": "Percentual de acrescimo ao valor original por meio de aditivos contratuais",
        "unit": "percent",
    },
    "excessive_amendments": {
        "label": "Aditivos excessivos",
        "description": "Indica se ha mais de 3 aditivos ou se o valor aditado excede 50% do original",
        "unit": "boolean",
    },
    # ── T01 - Concentracao em Fornecedor ──────────────────────────────
    "hhi": {
        "label": "Indice HHI",
        "description": "Indice Herfindahl-Hirschman: mede concentracao de mercado entre fornecedores (0-10000, quanto maior, mais concentrado)",
        "unit": "number",
    },
    "top1_share": {
        "label": "Fatia do maior fornecedor",
        "description": "Percentual do valor total contratado que foi para o fornecedor dominante",
        "unit": "percent",
    },
    "n_winners": {
        "label": "Fornecedores vencedores",
        "description": "Quantidade de fornecedores distintos que venceram licitacoes neste grupo",
        "unit": "count",
    },
    "baseline_p90": {
        "label": "Baseline P90",
        "description": "Percentil 90 do HHI historico — 90% dos grupos tem HHI abaixo deste valor",
        "unit": "number",
    },
    "baseline_p95": {
        "label": "Baseline P95",
        "description": "Percentil 95 do HHI historico — apenas 5% dos grupos ultrapassam este limiar",
        "unit": "number",
    },
    "catmat_group": {
        "label": "Grupo CATMAT",
        "description": "Codigo de classificacao de materiais/servicos do governo federal",
        "unit": "text",
    },
    # ── T02 - Baixa Competicao ────────────────────────────────────────
    "avg_bidders": {
        "label": "Media de licitantes",
        "description": "Numero medio de participantes nas licitacoes do grupo",
        "unit": "number",
    },
    "pct_single_bidder": {
        "label": "% licitante unico",
        "description": "Percentual de licitacoes com apenas um participante",
        "unit": "percent",
    },
    "n_processes": {
        "label": "Processos analisados",
        "description": "Quantidade de processos licitatorios avaliados no grupo",
        "unit": "count",
    },
    # ── T03 - Fracionamento de Despesa ────────────────────────────────
    "cluster_count": {
        "label": "Compras no cluster",
        "description": "Quantidade de compras agrupadas em janela temporal de 30 dias",
        "unit": "count",
    },
    "n_purchases": {
        "label": "Compras no cluster",
        "description": "Quantidade de compras diretas agrupadas na mesma janela temporal",
        "unit": "count",
    },
    "cluster_value": {
        "label": "Valor acumulado",
        "description": "Valor total acumulado das compras no cluster temporal",
        "unit": "brl",
    },
    "total_value_brl": {
        "label": "Valor total",
        "description": "Valor total acumulado das compras consideradas no sinal",
        "unit": "brl",
    },
    "threshold_ratio": {
        "label": "Razao valor/limite",
        "description": "Quanto o valor acumulado excede o limite legal de dispensa de licitacao",
        "unit": "ratio",
    },
    "ratio": {
        "label": "Razao valor/limite",
        "description": "Quantas vezes o valor total supera o limite legal de dispensa",
        "unit": "ratio",
    },
    "avg_value": {
        "label": "Valor medio",
        "description": "Valor medio por compra dentro do cluster temporal",
        "unit": "brl",
    },
    "avg_value_brl": {
        "label": "Valor medio por compra",
        "description": "Valor medio por compra dentro do cluster analisado",
        "unit": "brl",
    },
    "threshold_brl": {
        "label": "Limite legal",
        "description": "Limite legal de dispensa usado na comparacao do sinal",
        "unit": "brl",
    },
    # ── T04 - Aditivo Outlier ─────────────────────────────────────────
    "amendment_count": {
        "label": "Quantidade de aditivos",
        "description": "Numero de termos aditivos no contrato analisado",
        "unit": "count",
    },
    "amendment_value_pct": {
        "label": "% de acrescimo",
        "description": "Percentual de acrescimo ao valor original do contrato via aditivos",
        "unit": "percent",
    },
    "original_value": {
        "label": "Valor original",
        "description": "Valor original do contrato antes dos aditivos",
        "unit": "brl",
    },
    "amended_value": {
        "label": "Valor aditado",
        "description": "Valor total apos aplicacao dos aditivos",
        "unit": "brl",
    },
    # ── T05 - Preco Outlier ───────────────────────────────────────────
    "unit_price": {
        "label": "Preco unitario",
        "description": "Preco pago por unidade no contrato analisado",
        "unit": "brl",
    },
    "overpricing_ratio": {
        "label": "Razao de sobrepreco",
        "description": "Quantas vezes o preco pago excede a mediana historica para o mesmo item",
        "unit": "ratio",
    },
    "baseline_median": {
        "label": "Mediana historica",
        "description": "Valor mediano pago pelo mesmo item em compras anteriores",
        "unit": "brl",
    },
    "item_description": {
        "label": "Descricao do item",
        "description": "Descricao do material ou servico comparado",
        "unit": "text",
    },
    # ── T06 - Proxy de Empresa de Fachada ─────────────────────────────
    "composite_score": {
        "label": "Score composto",
        "description": "Pontuacao ponderada combinando idade da empresa, capital social, endereco compartilhado e volume de contratos",
        "unit": "score",
    },
    "age_score": {
        "label": "Score de idade",
        "description": "Pontuacao baseada na idade da empresa (empresas muito novas recebem pontuacao mais alta)",
        "unit": "score",
    },
    "capital_score": {
        "label": "Score de capital",
        "description": "Relacao entre o capital social declarado e o volume de contratos (capital muito baixo indica risco)",
        "unit": "score",
    },
    "address_score": {
        "label": "Score de endereco",
        "description": "Pontuacao baseada em compartilhamento de endereco com outras empresas contratadas",
        "unit": "score",
    },
    "company_age_days": {
        "label": "Idade da empresa",
        "description": "Idade da empresa em dias desde a data de abertura",
        "unit": "days",
    },
    "capital_social": {
        "label": "Capital social",
        "description": "Capital social declarado na Receita Federal",
        "unit": "brl",
    },
    # ── T07 - Rede de Cartel ──────────────────────────────────────────
    "cluster_size": {
        "label": "Tamanho do cluster",
        "description": "Quantidade de empresas no agrupamento suspeito de cartel",
        "unit": "count",
    },
    "shared_wins": {
        "label": "Vitorias compartilhadas",
        "description": "Quantidade de licitacoes vencidas pelo grupo de empresas suspeitas",
        "unit": "count",
    },
    "rotation_score": {
        "label": "Score de rotacao",
        "description": "Indicador de rotacao sistematica de vencedores entre empresas do grupo",
        "unit": "score",
    },
    # ── T08 - Sancao x Contrato ───────────────────────────────────────
    "sanction_active": {
        "label": "Sancao vigente",
        "description": "Indica se a entidade possui sancao (CEIS/CNEP) ativa no periodo do contrato",
        "unit": "boolean",
    },
    "overlap_days": {
        "label": "Dias de sobreposicao",
        "description": "Dias em que o contrato e a sancao se sobrepoem temporalmente",
        "unit": "days",
    },
    "sanction_type": {
        "label": "Tipo de sancao",
        "description": "Tipo da sancao registrada (CEIS, CNEP, etc.)",
        "unit": "text",
    },
    "contract_value": {
        "label": "Valor do contrato",
        "description": "Valor do contrato firmado durante vigencia da sancao",
        "unit": "brl",
    },
    # ── T09 - Proxy de Folha Fantasma ─────────────────────────────────
    "ghost_indicators": {
        "label": "Indicadores fantasma",
        "description": "Quantidade de indicadores de folha fantasma detectados",
        "unit": "count",
    },
    "payroll_anomaly_score": {
        "label": "Score de anomalia",
        "description": "Pontuacao de anomalia na folha de pagamento comparada ao baseline",
        "unit": "score",
    },
    # ── T11 - Jogo de Planilha ────────────────────────────────────────
    "n_items_overpriced": {
        "label": "Itens com sobrepreco",
        "description": "Itens com preco unitario maior ou igual a 2x a referencia SINAPI/Painel de Precos",
        "unit": "count",
    },
    "quantity_increase_value": {
        "label": "Valor do aumento de quantidade",
        "description": "Impacto financeiro do aumento de quantidade nos itens sobrepreçados via aditivo",
        "unit": "brl",
    },
    "net_overcharge_brl": {
        "label": "Sobrepreco liquido estimado",
        "description": "Delta financeiro total estimado do jogo de planilha (excesso de preco * quantidade aumentada)",
        "unit": "brl",
    },
    "price_ratio_max": {
        "label": "Razao maxima preco/referencia",
        "description": "Maior razao entre preco unitario contratado e a referencia SINAPI para um item",
        "unit": "ratio",
    },
    # ── T12 - Edital Direcionado ──────────────────────────────────────
    "restrictiveness_score": {
        "label": "Score de restricao",
        "description": "Pontuacao de especificidade do edital: combina media de licitantes e percentual com participante unico",
        "unit": "score",
    },
    "repeat_winner": {
        "label": "Vencedor recorrente",
        "description": "Indica se o mesmo fornecedor venceu 3 ou mais licitacoes nesta entidade e grupo CATMAT",
        "unit": "boolean",
    },
    "single_eligible": {
        "label": "Unico habilitado",
        "description": "Indica se 50% ou mais dos processos tiveram apenas um participante habilitado",
        "unit": "boolean",
    },
    "win_count": {
        "label": "Vitorias do fornecedor",
        "description": "Numero de licitacoes vencidas pelo mesmo fornecedor no grupo analisado",
        "unit": "count",
    },
    # ── T13 - Conflito de Interesses ──────────────────────────────────
    "relationship_score": {
        "label": "Score de relacionamento",
        "description": "Pontuacao ponderada de vinculos entre o agente publico contratante e o fornecedor vencedor",
        "unit": "score",
    },
    "n_shared_indicators": {
        "label": "Indicadores compartilhados",
        "description": "Numero de vinculos identificados (endereco, telefone, socio, parentesco, etc.)",
        "unit": "count",
    },
    "n_contracts_affected": {
        "label": "Contratos afetados",
        "description": "Quantidade de contratos/licitacoes com potencial conflito de interesses",
        "unit": "count",
    },
    "kinship_degree": {
        "label": "Grau de parentesco estimado",
        "description": "Grau de parentesco estimado via heuristica de nome e endereco (0 = sem parentesco detectado)",
        "unit": "count",
    },
    # ── T14 - Sequencia de Favorecimento Contratual ───────────────────
    "n_signals_triggered": {
        "label": "Sinais componentes",
        "description": "Numero de sinais individuais de tipologias distintas ativados para a mesma entidade",
        "unit": "count",
    },
    "meta_score": {
        "label": "Score meta-composto",
        "description": "Pontuacao ponderada dos sinais componentes por severidade (CRITICAL=3, HIGH=2, MEDIUM=1)",
        "unit": "score",
    },
    "sub_typologies": {
        "label": "Tipologias componentes",
        "description": "Codigos das tipologias individuais que compoe o sinal composto",
        "unit": "text",
    },
    "n_component_typologies": {
        "label": "Tipologias distintas ativadas",
        "description": "Numero de tipologias distintas que contribuiram para o sinal composto",
        "unit": "count",
    },
    # ── T15 - Inexigibilidade Indevida ────────────────────────────────
    "n_alternative_suppliers": {
        "label": "Fornecedores alternativos",
        "description": "Numero de fornecedores qualificados identificados no mesmo grupo CATMAT em licitacoes competitivas",
        "unit": "count",
    },
    "n_inexigibilidade_contracts": {
        "label": "Contratos por inexigibilidade",
        "description": "Numero de contratos firmados sem licitacao com o mesmo fornecedor nesta entidade",
        "unit": "count",
    },
    "repeat_inexigibilidade": {
        "label": "Padrao repetitivo",
        "description": "Indica se o mesmo fornecedor recebeu 2 ou mais contratos por inexigibilidade na mesma entidade",
        "unit": "boolean",
    },
    # ── T16 - Clientelismo Orcamentario-Contratual ────────────────────
    "plano_trabalho_registered": {
        "label": "Plano de trabalho registrado",
        "description": "Indica se existe plano de trabalho registrado no SICONV dentro de 90 dias da transferencia",
        "unit": "boolean",
    },
    "value_vs_revenue_ratio": {
        "label": "Emenda / Receita propria",
        "description": "Razao entre o valor da emenda e a receita propria anual do municipio beneficiario",
        "unit": "ratio",
    },
    "relator_hhi": {
        "label": "HHI do relator",
        "description": "Concentracao das emendas do parlamentar por municipio beneficiario (HHI 0-1, quanto maior mais concentrado)",
        "unit": "number",
    },
    "recipient_sanctioned": {
        "label": "Beneficiario sancionado",
        "description": "Indica se o municipio/entidade beneficiaria consta no CEIS com sancao ativa",
        "unit": "boolean",
    },
    "n_flags": {
        "label": "Indicadores de risco",
        "description": "Total de bandeiras de risco detectadas (sem plano de trabalho, HHI alto, beneficiario sancionado, etc.)",
        "unit": "count",
    },
    # ── T17 - Lavagem via Camadas Societarias ─────────────────────────
    "cycle_length": {
        "label": "Comprimento do ciclo",
        "description": "Numero de saltos no ciclo de retorno dos recursos ao beneficiario original",
        "unit": "count",
    },
    "intra_community_value": {
        "label": "Valor intra-comunidade",
        "description": "Volume financeiro transferido dentro do cluster societario suspeito",
        "unit": "brl",
    },
    "ubo_convergence": {
        "label": "Convergencia de beneficiario final",
        "description": "Indica se o fluxo financeiro converge para o mesmo beneficiario final em 2 ou menos saltos",
        "unit": "boolean",
    },
    "n_intra_subcontractors": {
        "label": "Subcontratados intra-comunidade",
        "description": "Numero de subcontratados pertencentes ao mesmo cluster societario do vencedor",
        "unit": "count",
    },
    # ── T18 - Acumulo Ilegal de Cargos ────────────────────────────────
    "n_organs": {
        "label": "Orgaos simultaneos",
        "description": "Numero de orgaos com vinculo ativo simultaneo para o mesmo servidor",
        "unit": "count",
    },
    "ceaf_match": {
        "label": "Correspondencia CEAF",
        "description": "Indica se o CPF do servidor consta no Cadastro de Expulsoes da Administracao Federal (CEAF/CGU)",
        "unit": "boolean",
    },
    "n_overlap_pairs": {
        "label": "Pares com sobreposicao",
        "description": "Numero de pares de orgaos com periodo de sobreposicao de vinculo detectado",
        "unit": "count",
    },
    # ── Generic / Cross-typology ──────────────────────────────────────
    "gated_by_completeness": {
        "label": "Rebaixado por completude",
        "description": "Severidade foi rebaixada pois as evidencias disponiveis sao insuficientes para sustentar a classificacao original",
        "unit": "boolean",
    },
    "risk_score": {
        "label": "Score de risco",
        "description": "Pontuacao geral de risco calculada pela tipologia",
        "unit": "score",
    },
    "sample_size": {
        "label": "Tamanho da amostra",
        "description": "Quantidade de registros utilizados na analise",
        "unit": "count",
    },
}


TYPOLOGY_FACTOR_OVERRIDES: dict[str, dict[str, dict[str, str]]] = {
    "T03": {
        "span_days": {
            "label": "Duracao da janela",
            "description": "Periodo em dias da janela temporal entre a primeira e a ultima compra do cluster",
            "unit": "days",
        },
    },
}


def get_factor_descriptions(
    factors: dict,
    typology_code: str | None = None,
) -> dict[str, dict[str, str]]:
    """Return metadata only for factor keys present in the given dict."""
    metadata: dict[str, dict[str, str]] = {}
    overrides = TYPOLOGY_FACTOR_OVERRIDES.get(typology_code or "", {})

    for key in factors:
        if key in overrides:
            metadata[key] = overrides[key]
            continue
        if key in FACTOR_METADATA:
            metadata[key] = FACTOR_METADATA[key]

    return metadata


# ── Typology-level metadata (corruption type, sphere, evidence level) ─────
# Maps typology code to legal/analytical context per legal-first doc.

TYPOLOGY_LEGAL_METADATA: dict[str, dict[str, list[str] | str]] = {
    "T01": {
        "corruption_types": ["fraude_licitatoria"],
        "spheres": ["administrativa"],
        "evidence_level": "indirect",
        "description_legal": "Concentracao de mercado pode indicar conluio ou captura de fornecedor unico sem competicao real.",
        "law_articles": [
            {"law_name": "Lei 14.133/2021", "article": "Art. 9°, IV", "violation_type": "fraude_licitatoria"},
        ],
    },
    "T02": {
        "corruption_types": ["fraude_licitatoria"],
        "spheres": ["administrativa"],
        "evidence_level": "indirect",
        "description_legal": "Baixa competicao sistematica pode indicar restricao deliberada de participantes.",
        "law_articles": [
            {"law_name": "Lei 14.133/2021", "article": "Art. 337-F", "violation_type": "fraude_licitatoria"},
        ],
    },
    "T03": {
        "corruption_types": ["fraude_licitatoria"],
        "spheres": ["administrativa"],
        "evidence_level": "direct",
        "description_legal": "Fracionamento de despesa para evitar licitacao obrigatoria e infracoes a Lei 14.133/2021.",
        "law_articles": [
            {"law_name": "Lei 14.133/2021", "article": "Art. 337-E", "violation_type": "fraude_licitatoria"},
            {"law_name": "Lei 8.666/1993", "article": "Art. 24", "violation_type": "fraude_licitatoria"},
        ],
    },
    "T04": {
        "corruption_types": ["fraude_licitatoria", "corrupcao_passiva"],
        "spheres": ["administrativa"],
        "evidence_level": "indirect",
        "description_legal": "Aditivos excessivos podem indicar sobrepreco oculto ou favorecimento contratual.",
        "law_articles": [
            {"law_name": "Lei 14.133/2021", "article": "Art. 337-K", "violation_type": "fraude_licitatoria"},
        ],
    },
    "T05": {
        "corruption_types": ["fraude_licitatoria"],
        "spheres": ["administrativa", "privada"],
        "evidence_level": "direct",
        "description_legal": "Sobrepreco em relacao a mediana historica sugere superfaturamento.",
        "law_articles": [
            {"law_name": "Lei 14.133/2021", "article": "Art. 337-K", "violation_type": "fraude_licitatoria"},
            {"law_name": "Código Penal", "article": "Art. 312", "violation_type": "peculato"},
        ],
    },
    "T06": {
        "corruption_types": ["lavagem", "corrupcao_ativa"],
        "spheres": ["privada", "administrativa"],
        "evidence_level": "proxy",
        "description_legal": "Empresa com indicadores de fachada (baixo capital, recente, endereco compartilhado) pode ser veiculo de desvio.",
        "law_articles": [
            {"law_name": "Lei 9.613/1998", "article": "Art. 1°", "violation_type": "lavagem"},
            {"law_name": "Lei 12.846/2013", "article": "Art. 5°", "violation_type": "corrupcao_ativa"},
        ],
    },
    "T07": {
        "corruption_types": ["fraude_licitatoria", "corrupcao_ativa"],
        "spheres": ["privada", "sistemica"],
        "evidence_level": "indirect",
        "description_legal": "Padrao de rodizio de vencedores e propostas coordenadas indica possivel cartel (CADE/Lei 12.846).",
        "law_articles": [
            {"law_name": "Lei 12.529/2011", "article": "Art. 36", "violation_type": "corrupcao_ativa"},
            {"law_name": "Lei 14.133/2021", "article": "Art. 337-F", "violation_type": "fraude_licitatoria"},
        ],
    },
    "T08": {
        "corruption_types": ["corrupcao_passiva", "prevaricacao"],
        "spheres": ["administrativa"],
        "evidence_level": "direct",
        "description_legal": "Contratar entidade com sancao ativa viola normas de impedimento e pode indicar favorecimento.",
        "law_articles": [
            {"law_name": "Lei 8.429/1992", "article": "Art. 9°", "violation_type": "corrupcao_passiva"},
            {"law_name": "Lei 14.133/2021", "article": "Art. 14", "violation_type": "fraude_licitatoria"},
        ],
    },
    "T09": {
        "corruption_types": ["peculato"],
        "spheres": ["administrativa"],
        "evidence_level": "proxy",
        "description_legal": "Anomalias em folha de pagamento podem indicar folha fantasma (art. 312 CP).",
        "law_articles": [
            {"law_name": "Código Penal", "article": "Art. 312", "violation_type": "peculato"},
        ],
    },
    "T10": {
        "corruption_types": ["peculato", "fraude_licitatoria"],
        "spheres": ["administrativa"],
        "evidence_level": "indirect",
        "description_legal": "Terceirizacao com concentracao excessiva e aditivos pode ocultar desvio ou sobrepreco sistematico.",
        "law_articles": [
            {"law_name": "Código Penal", "article": "Art. 312", "violation_type": "peculato"},
            {"law_name": "Lei 14.133/2021", "article": "Art. 337-K", "violation_type": "fraude_licitatoria"},
        ],
    },
    "T11": {
        "corruption_types": ["fraude_licitatoria", "peculato"],
        "spheres": ["administrativa", "privada"],
        "evidence_level": "direct",
        "description_legal": "Jogo de planilha: manipulacao de precos unitarios para desviar via aditivos (CGU Guia Superfaturamento 2025, Tipo 4; TCU Fiscobras achado #1).",
        "law_articles": [
            {"law_name": "Lei 14.133/2021", "article": "Art. 337-K", "violation_type": "fraude_licitatoria"},
            {"law_name": "Código Penal", "article": "Art. 312", "violation_type": "peculato"},
        ],
    },
    "T12": {
        "corruption_types": ["fraude_licitatoria", "corrupcao_ativa_passiva"],
        "spheres": ["administrativa"],
        "evidence_level": "indirect",
        "description_legal": "Edital direcionado: exigencias restritivas eliminam competidores, garantindo vitoria do fornecedor pre-escolhido (Lei 14.133/2021, Art. 9°, IV).",
        "law_articles": [
            {"law_name": "Lei 14.133/2021", "article": "Art. 9°, IV", "violation_type": "fraude_licitatoria"},
        ],
    },
    "T13": {
        "corruption_types": ["nepotismo_clientelismo", "corrupcao_ativa_passiva"],
        "spheres": ["administrativa", "politica"],
        "evidence_level": "indirect",
        "description_legal": "Conflito de interesses: vinculo familiar, comercial ou societario entre agente publico contratante e fornecedor vencedor (Lei 12.813/2013; TCU Acordao 1798/2024).",
        "law_articles": [
            {"law_name": "Lei 8.429/1992", "article": "Art. 9°, I", "violation_type": "corrupcao_passiva"},
            {"law_name": "Lei 12.813/2013", "article": "Art. 5°", "violation_type": "nepotismo_clientelismo"},
        ],
    },
    "T14": {
        "corruption_types": ["corrupcao_ativa_passiva", "fraude_licitatoria"],
        "spheres": ["administrativa", "sistemica"],
        "evidence_level": "indirect",
        "description_legal": "Sequencia de favorecimento: acumulo persistente de sinais T01/T02/T04/T05 para o mesmo par entidade-fornecedor indica captura sistematica (CP Arts. 317/333).",
        "law_articles": [
            {"law_name": "Código Penal", "article": "Art. 317", "violation_type": "corrupcao_passiva"},
            {"law_name": "Código Penal", "article": "Art. 333", "violation_type": "corrupcao_ativa"},
        ],
    },
    "T15": {
        "corruption_types": ["fraude_licitatoria", "prevaricacao"],
        "spheres": ["administrativa"],
        "evidence_level": "indirect",
        "description_legal": "Inexigibilidade indevida: contrato declarado como inexigivel quando existem fornecedores alternativos qualificados (Lei 14.133/2021, Art. 74; Lei 8.429/92, Art. 10, VII).",
        "law_articles": [
            {"law_name": "Lei 14.133/2021", "article": "Art. 74", "violation_type": "fraude_licitatoria"},
            {"law_name": "Lei 8.429/1992", "article": "Art. 10, VII", "violation_type": "corrupcao_passiva"},
        ],
    },
    "T16": {
        "corruption_types": ["nepotismo_clientelismo", "peculato"],
        "spheres": ["politica", "administrativa"],
        "evidence_level": "indirect",
        "description_legal": "Clientelismo orcamentario: emendas parlamentares sem plano de trabalho ou desproporcionais a capacidade do municipio (TCU Acordao 518/2023; STF Min. Dino 2024).",
        "law_articles": [
            {"law_name": "CF/88", "article": "Art. 166, §9°", "violation_type": "nepotismo_clientelismo"},
            {"law_name": "Código Penal", "article": "Art. 312", "violation_type": "peculato"},
        ],
    },
    "T17": {
        "corruption_types": ["lavagem"],
        "spheres": ["privada", "sistemica"],
        "evidence_level": "indirect",
        "description_legal": "Lavagem via camadas societarias: fluxo circular de recursos por estrutura de empresas relacionadas oculta origem (Lei 9.613/1998; FATF Recomendacao 24).",
        "law_articles": [
            {"law_name": "Lei 9.613/1998", "article": "Art. 1°", "violation_type": "lavagem"},
        ],
    },
    "T18": {
        "corruption_types": ["peculato", "nepotismo_clientelismo"],
        "spheres": ["administrativa"],
        "evidence_level": "direct",
        "description_legal": "Acumulo ilegal de cargos: servidor em dois ou mais orgaos simultaneamente (CF/88 Art. 37, XVI-XVII) ou expulso (CEAF) como socio de empresa contratante.",
        "law_articles": [
            {"law_name": "CF/88", "article": "Art. 37, XVI–XVII", "violation_type": "nepotismo_clientelismo"},
            {"law_name": "Lei 8.112/1990", "article": "Art. 118", "violation_type": "peculato"},
        ],
    },
    "T19": {
        "corruption_types": ["fraude_licitatoria"],
        "spheres": ["privada", "sistemica"],
        "evidence_level": "indirect",
        "description_legal": "Rodizio sistematico de vencedores entre empresas participantes sugere conluio cartelizado em licitacoes publicas.",
        "law_articles": [
            {"law_name": "Lei 12.529/2011", "article": "Art. 36, §3°, I", "violation_type": "fraude_licitatoria"},
            {"law_name": "Lei 14.133/2021", "article": "Art. 337-F", "violation_type": "fraude_licitatoria"},
        ],
    },
    "T20": {
        "corruption_types": ["fraude_licitatoria"],
        "spheres": ["privada"],
        "evidence_level": "indirect",
        "description_legal": "Participacao reiterada em licitacoes sem nenhuma vitoria, sempre ao lado do mesmo vencedor, indica licitante fantasma para simular competicao.",
        "law_articles": [
            {"law_name": "Lei 14.133/2021", "article": "Art. 337-E", "violation_type": "fraude_licitatoria"},
            {"law_name": "Lei 8.429/1992", "article": "Art. 10, VIII", "violation_type": "fraude_licitatoria"},
        ],
    },
    "T21": {
        "corruption_types": ["fraude_licitatoria"],
        "spheres": ["privada", "sistemica"],
        "evidence_level": "indirect",
        "description_legal": "Cluster colusivo detectado por analise de rede: grupo de empresas com taxa dominante de vitoria conjunta em licitacoes da mesma categoria.",
        "law_articles": [
            {"law_name": "Lei 12.529/2011", "article": "Art. 36", "violation_type": "fraude_licitatoria"},
            {"law_name": "Lei 14.133/2021", "article": "Art. 337-F", "violation_type": "fraude_licitatoria"},
        ],
    },
    "T22": {
        "corruption_types": ["nepotismo_clientelismo", "corrupcao_ativa_passiva"],
        "spheres": ["politica", "privada"],
        "evidence_level": "indirect",
        "description_legal": "Favorecimento politico: doacao eleitoral seguida de contrato publico em curto intervalo indica troca de favores entre doador e ente publico.",
        "law_articles": [
            {"law_name": "Lei 9.504/1997", "article": "Art. 81-A", "violation_type": "corrupcao_ativa_passiva"},
            {"law_name": "Lei 8.429/1992", "article": "Art. 9°, III", "violation_type": "nepotismo_clientelismo"},
        ],
    },
}


CORRUPTION_TYPE_LABELS: dict[str, str] = {
    "corrupcao_ativa": "Corrupcao Ativa (art. 333 CP)",
    "corrupcao_passiva": "Corrupcao Passiva (art. 317 CP)",
    "concussao": "Concussao (art. 316 CP)",
    "prevaricacao": "Prevaricacao (art. 319 CP)",
    "peculato": "Peculato (art. 312 CP)",
    "lavagem": "Lavagem de Dinheiro (Lei 9.613/98)",
    "fraude_licitatoria": "Fraude em Licitacao (Lei 14.133/2021)",
    "nepotismo_clientelismo": "Nepotismo/Clientelismo (Decreto 7.203/2010)",
}

SPHERE_LABELS: dict[str, str] = {
    "politica": "Politica (macro)",
    "administrativa": "Administrativa/Burocratica",
    "privada": "Privada",
    "sistemica": "Sistemica",
}


def get_typology_codes_for_filter(
    corruption_type: str | None = None,
    sphere: str | None = None,
) -> list[str] | None:
    """Return typology codes matching the given legal classification filters.

    Returns None if no filter is applied (i.e. both params are None).
    Returns an empty list if filters match no typology.
    """
    if corruption_type is None and sphere is None:
        return None

    codes: list[str] = []
    for code, meta in TYPOLOGY_LEGAL_METADATA.items():
        ct_match = corruption_type is None or corruption_type in meta.get("corruption_types", [])
        sp_match = sphere is None or sphere in meta.get("spheres", [])
        if ct_match and sp_match:
            codes.append(code)
    return codes
