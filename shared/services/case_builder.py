"""Case auto-creation from ungrouped risk signals.

Groups related signals into investigation cases by:
1. Entity cluster overlap (signals sharing the same entity cluster)
2. Time window proximity (signals within 90 days of each other)
"""

import uuid
from collections import defaultdict
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from sqlalchemy.orm import selectinload

from shared.logging import log
from shared.models.orm import Case, CaseItem, Entity, RiskSignal, Typology
from shared.services.legal_inference import infer_legal_hypotheses_sync


_SEVERITY_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}

_TYPOLOGY_SHORT: dict[str, str] = {
    "T01": "Concentracao",
    "T02": "Baixa Competicao",
    "T03": "Fracionamento",
    "T04": "Aditivo Outlier",
    "T05": "Preco Outlier",
    "T06": "Empresa de Fachada",
    "T07": "Rede de Cartel",
    "T08": "Sancao x Contrato",
    "T09": "Folha Fantasma",
    "T10": "Terceirizacao",
    "T11": "Jogo de Planilha",
    "T12": "Edital Direcionado",
    "T13": "Conflito de Interesse",
    "T14": "Favorecimento Composto",
    "T15": "Inexigibilidade Indevida",
    "T16": "Clientelismo Orcamentario",
    "T17": "Lavagem Societaria",
    "T18": "Acumulo de Cargos",
    "T19": "Rodizio de Vencedores",
    "T20": "Licitante Fantasma",
    "T21": "Cluster Colusivo",
    "T22": "Favorecimento Politico",
}


def _max_severity(*severities: str) -> str:
    """Return the highest severity from a list."""
    return max(severities, key=lambda s: _SEVERITY_ORDER.get(s, 0))


def _should_create_case(signals: list) -> bool:
    """Accept 2+ signal groups, or single HIGH/CRITICAL signals."""
    if len(signals) >= 2:
        return True
    if signals:
        return signals[0].severity in ("high", "critical")
    return False


def classify_case_type(typology_codes: set[str]) -> str:
    """Classify a case by its dominant typology pattern.

    Rules are checked in priority order (highest specificity first).
    Returns a string code for the case type.
    """
    codes = frozenset(typology_codes)

    # Priority order: most specific patterns first
    if "T07" in codes:
        return "CARTEL_NETWORK"
    if "T21" in codes:
        return "CARTEL_NETWORK"
    if "T19" in codes or "T20" in codes:
        return "CARTEL_NETWORK"
    if "T13" in codes:
        return "CONFLICT_OF_INTEREST"
    if "T22" in codes:
        return "CONFLICT_OF_INTEREST"
    if "T08" in codes:
        return "SANCTIONED_ENTITY"
    if "T17" in codes:
        return "MONEY_LAUNDERING_PROXY"
    if "T18" in codes:
        return "ILLEGAL_ACCUMULATION"
    if {"T02", "T12"}.issubset(codes):
        return "DIRECTED_TENDER"
    if "T12" in codes:
        return "DIRECTED_TENDER"
    if {"T03", "T11"}.issubset(codes) or {"T03", "T05"}.issubset(codes):
        return "PROCUREMENT_FRAUD"
    if "T14" in codes and len(codes) >= 3:
        return "HIGH_RISK_COMPOUND"
    if "T14" in codes:
        return "COMPOUND_FAVORITISM"
    if len(codes) >= 4:
        return "HIGH_RISK_COMPOUND"
    return "OTHER"


def build_cases_from_signals(session: Session) -> list[Case]:
    """Group uncased signals into cases by entity cluster + time window.

    Steps:
    1. Get signals not yet linked to any case.
    2. Group by overlapping entity_ids (using cluster_id when available).
    3. For each cluster with 2+ signals: create Case, link via CaseItem.
    4. Set case severity = max(signal severities).
    """
    # 1. Get all signal IDs already in cases
    cased_stmt = select(CaseItem.signal_id)
    cased_result = session.execute(cased_stmt)
    cased_signal_ids = {row[0] for row in cased_result}

    # 2. Get uncased signals (with typology eagerly loaded for title generation)
    signal_stmt = (
        select(RiskSignal)
        .options(selectinload(RiskSignal.typology))
        .order_by(RiskSignal.created_at.desc())
    )
    all_signals = session.execute(signal_stmt).scalars().all()

    uncased = [s for s in all_signals if s.id not in cased_signal_ids]

    if not uncased:
        log.info("case_builder.no_uncased_signals")
        return []

    # 3. Build entity -> cluster_id mapping
    all_entity_ids: set[uuid.UUID] = set()
    for s in uncased:
        for eid_str in s.entity_ids:
            try:
                all_entity_ids.add(uuid.UUID(str(eid_str)))
            except (ValueError, TypeError):
                pass

    cluster_map: dict[uuid.UUID, uuid.UUID] = {}
    if all_entity_ids:
        # Chunked to avoid asyncpg/psycopg 32K param limit at scale
        _entity_id_list = list(all_entity_ids)
        _IN_CHUNK = 5_000
        entities: list[Entity] = []
        for _i in range(0, len(_entity_id_list), _IN_CHUNK):
            _chunk = _entity_id_list[_i : _i + _IN_CHUNK]
            entities.extend(
                session.execute(select(Entity).where(Entity.id.in_(_chunk))).scalars().all()
            )
        for e in entities:
            if e.cluster_id is not None:
                cluster_map[e.id] = e.cluster_id
            else:
                cluster_map[e.id] = e.id  # Self-cluster

    # 4. Group signals by effective cluster
    # A signal belongs to a cluster if any of its entity_ids maps to that cluster
    cluster_signals: dict[uuid.UUID, list[RiskSignal]] = defaultdict(list)
    ungrouped: list[RiskSignal] = []

    for s in uncased:
        signal_clusters: set[uuid.UUID] = set()
        for eid_str in s.entity_ids:
            try:
                eid = uuid.UUID(str(eid_str))
                cid = cluster_map.get(eid)
                if cid is not None:
                    signal_clusters.add(cid)
            except (ValueError, TypeError):
                pass

        if signal_clusters:
            # Assign to first cluster (arbitrary but deterministic)
            primary_cluster = sorted(signal_clusters)[0]
            cluster_signals[primary_cluster].append(s)
        else:
            ungrouped.append(s)

    # 5. Pre-fetch ALL entity names to avoid N+1 queries in the grouping loop
    _all_group_entity_ids: set[uuid.UUID] = set()
    for _sigs in cluster_signals.values():
        for _s in _sigs:
            for _eid_str in _s.entity_ids:
                try:
                    _all_group_entity_ids.add(uuid.UUID(str(_eid_str)))
                except (ValueError, TypeError):
                    pass
    _entity_name_cache: dict[uuid.UUID, str] = {}
    if _all_group_entity_ids:
        _eid_list = list(_all_group_entity_ids)
        for _i in range(0, len(_eid_list), _IN_CHUNK):
            _chunk = _eid_list[_i : _i + _IN_CHUNK]
            for _e in session.execute(select(Entity).where(Entity.id.in_(_chunk))).scalars().all():
                if _e.name:
                    _entity_name_cache[_e.id] = _e.name

    # Create cases from clusters with 2+ signals
    created_cases: list[Case] = []

    for cluster_id, signals in cluster_signals.items():
        if not _should_create_case(signals):
            continue

        # Sub-group by time proximity (90-day windows)
        signals_sorted = sorted(
            signals, key=lambda s: s.created_at or s.period_start
        )
        time_groups: list[list[RiskSignal]] = []
        current_group: list[RiskSignal] = [signals_sorted[0]]

        for s in signals_sorted[1:]:
            prev_time = current_group[-1].created_at or current_group[-1].period_start
            curr_time = s.created_at or s.period_start
            if prev_time and curr_time and (curr_time - prev_time) <= timedelta(days=90):
                current_group.append(s)
            else:
                if _should_create_case(current_group):
                    time_groups.append(current_group)
                current_group = [s]

        if _should_create_case(current_group):
            time_groups.append(current_group)

        for group in time_groups:
            max_sev = group[0].severity
            for s in group[1:]:
                max_sev = _max_severity(max_sev, s.severity)

            typology_codes: set[str] = set()
            group_entity_ids: set[uuid.UUID] = set()
            for s in group:
                if hasattr(s, "typology") and s.typology:
                    typology_codes.add(s.typology.code)
                for eid_str in s.entity_ids:
                    try:
                        group_entity_ids.add(uuid.UUID(str(eid_str)))
                    except (ValueError, TypeError):
                        pass

            # Resolve entity names from pre-fetched cache (no N+1 queries)
            entity_names: list[str] = [
                _entity_name_cache[eid]
                for eid in group_entity_ids
                if eid in _entity_name_cache
            ]

            # Build human-readable title
            typology_labels = sorted(
                _TYPOLOGY_SHORT.get(c, c) for c in typology_codes
            )
            if entity_names:
                primary_name = entity_names[0]
                title = f"Caso: {primary_name}"
                if typology_labels:
                    title += f" — {' e '.join(typology_labels[:3])}"
            else:
                title = f"Caso consolidado — {' e '.join(typology_labels[:3]) or 'cluster ' + str(cluster_id)[:8]}"

            # Calculate total value and period range from signals
            total_value = 0.0
            period_min = None
            period_max = None
            for s in group:
                val = (s.factors or {}).get("total_value_brl") or (s.factors or {}).get("cluster_value") or 0
                if isinstance(val, (int, float)):
                    total_value += val
                if s.period_start and (period_min is None or s.period_start < period_min):
                    period_min = s.period_start
                if s.period_end and (period_max is None or s.period_end > period_max):
                    period_max = s.period_end

            # Build summary with entity names
            names_str = ", ".join(entity_names[:5])
            if len(entity_names) > 5:
                names_str += f" e mais {len(entity_names) - 5}"
            summary = f"{len(group)} sinais de risco agrupados por entidade."
            if names_str:
                summary += f" Entidades: {names_str}."
            if typology_labels:
                summary += f" Tipologias: {', '.join(typology_labels)}."

            case = Case(
                title=title,
                status="open",
                severity=max_sev,
                summary=summary,
                case_type=classify_case_type(typology_codes),
                attrs={
                    "cluster_id": str(cluster_id),
                    "signal_count": len(group),
                    "entity_names": entity_names[:10],
                    "typology_codes": sorted(typology_codes),
                    "total_value_brl": total_value,
                    "period_start": period_min.isoformat() if period_min else None,
                    "period_end": period_max.isoformat() if period_max else None,
                    "grouping_rationale": (
                        f"Agrupado por {len(group_entity_ids)} entidade(s) compartilhada(s). "
                        f"Tipologias detectadas: {', '.join(sorted(typology_codes))}. "
                        f"Janela temporal: 90 dias."
                    ),
                },
            )
            session.add(case)
            session.flush()
            infer_legal_hypotheses_sync(case.id, typology_codes, session)

            for s in group:
                item = CaseItem(case_id=case.id, signal_id=s.id)
                session.add(item)

            created_cases.append(case)

    # 6. Create standalone cases for high-severity ungrouped signals
    for s in ungrouped:
        if s.severity not in ("high", "critical"):
            continue

        typology_code = s.typology.code if hasattr(s, "typology") and s.typology else "?"
        typology_label = _TYPOLOGY_SHORT.get(typology_code, typology_code)

        case = Case(
            title=f"Caso: sinal isolado — {typology_label}",
            status="open",
            severity=s.severity,
            summary=(
                f"Sinal de risco {s.severity} sem vínculo a cluster de entidades. "
                f"Tipologia: {typology_label}."
            ),
            case_type=classify_case_type({typology_code}),
            attrs={
                "signal_count": 1,
                "typology_codes": [typology_code],
                "ungrouped": True,
            },
        )
        session.add(case)
        session.flush()
        infer_legal_hypotheses_sync(case.id, {typology_code}, session)

        item = CaseItem(case_id=case.id, signal_id=s.id)
        session.add(item)
        created_cases.append(case)

    session.commit()

    log.info(
        "case_builder.done",
        cases_created=len(created_cases),
        uncased_signals=len(uncased),
    )
    return created_cases
