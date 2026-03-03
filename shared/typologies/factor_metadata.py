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
    },
    "T02": {
        "corruption_types": ["fraude_licitatoria"],
        "spheres": ["administrativa"],
        "evidence_level": "indirect",
        "description_legal": "Baixa competicao sistematica pode indicar restricao deliberada de participantes.",
    },
    "T03": {
        "corruption_types": ["fraude_licitatoria"],
        "spheres": ["administrativa"],
        "evidence_level": "direct",
        "description_legal": "Fracionamento de despesa para evitar licitacao obrigatoria e infracoes a Lei 14.133/2021.",
    },
    "T04": {
        "corruption_types": ["fraude_licitatoria", "corrupcao_passiva"],
        "spheres": ["administrativa"],
        "evidence_level": "indirect",
        "description_legal": "Aditivos excessivos podem indicar sobrepreco oculto ou favorecimento contratual.",
    },
    "T05": {
        "corruption_types": ["fraude_licitatoria"],
        "spheres": ["administrativa", "privada"],
        "evidence_level": "direct",
        "description_legal": "Sobrepreco em relacao a mediana historica sugere superfaturamento.",
    },
    "T06": {
        "corruption_types": ["lavagem", "corrupcao_ativa"],
        "spheres": ["privada", "administrativa"],
        "evidence_level": "proxy",
        "description_legal": "Empresa com indicadores de fachada (baixo capital, recente, endereco compartilhado) pode ser veiculo de desvio.",
    },
    "T07": {
        "corruption_types": ["fraude_licitatoria", "corrupcao_ativa"],
        "spheres": ["privada", "sistemica"],
        "evidence_level": "indirect",
        "description_legal": "Padrao de rodizio de vencedores e propostas coordenadas indica possivel cartel (CADE/Lei 12.846).",
    },
    "T08": {
        "corruption_types": ["corrupcao_passiva", "prevaricacao"],
        "spheres": ["administrativa"],
        "evidence_level": "direct",
        "description_legal": "Contratar entidade com sancao ativa viola normas de impedimento e pode indicar favorecimento.",
    },
    "T09": {
        "corruption_types": ["peculato"],
        "spheres": ["administrativa"],
        "evidence_level": "proxy",
        "description_legal": "Anomalias em folha de pagamento podem indicar folha fantasma (art. 312 CP).",
    },
    "T10": {
        "corruption_types": ["peculato", "fraude_licitatoria"],
        "spheres": ["administrativa"],
        "evidence_level": "indirect",
        "description_legal": "Terceirizacao com concentracao excessiva e aditivos pode ocultar desvio ou sobrepreco sistematico.",
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
