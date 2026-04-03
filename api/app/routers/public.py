import csv
import uuid
from datetime import datetime
from io import StringIO

from fastapi import APIRouter, HTTPException, Query, Response, status

from api.app.adapters.core_adapter import (
    adapter_get_baseline,
    adapter_get_case_provenance,
    adapter_get_entity_path,
    adapter_get_evidence_package_by_id,
    adapter_get_factor_descriptions,
    adapter_get_graph_neighborhood,
    adapter_get_org_summary,
    adapter_get_signal_by_id,
    adapter_get_signal_detail,
    adapter_get_signal_provenance,
    adapter_get_typology,
    adapter_get_typology_legal_metadata,
    adapter_list_typologies,
    adapter_replay_signal,
)
from api.app.adapters.core_adapter import (
    adapter_get_case_by_id as get_case_by_id,
)
from api.app.adapters.core_adapter import (
    adapter_get_case_entities_with_roles as get_case_entities_with_roles,
)
from api.app.adapters.core_adapter import (
    adapter_get_case_graph as get_case_graph,
)
from api.app.adapters.core_adapter import (
    adapter_get_coverage_v2_analytics as get_coverage_v2_analytics,
)
from api.app.adapters.core_adapter import (
    adapter_get_coverage_v2_map as get_coverage_v2_map,
)
from api.app.adapters.core_adapter import (
    adapter_get_coverage_v2_run_detail as get_coverage_v2_run_detail,
)
from api.app.adapters.core_adapter import (
    adapter_get_coverage_v2_source_preview as get_coverage_v2_source_preview,
)
from api.app.adapters.core_adapter import (
    adapter_get_coverage_v2_sources as get_coverage_v2_sources,
)

# ── Core adapter — dual-mode (direct DB in monorepo, HTTP in split) ───────────
from api.app.adapters.core_adapter import (
    adapter_get_coverage_v2_summary as get_coverage_v2_summary,
)
from api.app.adapters.core_adapter import (
    adapter_get_dossier_summary as get_dossier_summary,
)
from api.app.adapters.core_adapter import (
    adapter_get_dossier_timeline as get_dossier_timeline,
)
from api.app.adapters.core_adapter import (
    adapter_get_entity_by_id as get_entity_by_id,
)
from api.app.adapters.core_adapter import (
    adapter_get_public_sources as get_public_sources,
)
from api.app.adapters.core_adapter import (
    adapter_get_radar_v2_case_preview as get_radar_v2_case_preview,
)
from api.app.adapters.core_adapter import (
    adapter_get_radar_v2_cases as get_radar_v2_cases,
)
from api.app.adapters.core_adapter import (
    adapter_get_radar_v2_coverage as get_radar_v2_coverage,
)
from api.app.adapters.core_adapter import (
    adapter_get_radar_v2_signal_preview as get_radar_v2_signal_preview,
)
from api.app.adapters.core_adapter import (
    adapter_get_radar_v2_signals as get_radar_v2_signals,
)
from api.app.adapters.core_adapter import (
    adapter_get_radar_v2_summary as get_radar_v2_summary,
)
from api.app.adapters.core_adapter import (
    adapter_get_signal_evidence_page as get_signal_evidence_page,
)
from api.app.adapters.core_adapter import (
    adapter_get_signal_graph as get_signal_graph,
)
from api.app.adapters.core_adapter import (
    adapter_search_entities as search_entities,
)
from api.app.deps import DbSession, Pagination
from shared.models.contestation import Contestation

# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC API ROUTER — SPLIT-READY ARCHITECTURE
# ═══════════════════════════════════════════════════════════════════════════════
#
# This router is designed to work in TWO modes:
#
# 1. MONOREPO MODE (pre-split)
#    - Direct database access via SQLAlchemy async
#    - Uses core_adapter.py for all queries
#    - All endpoints return full internal data structures
#
# 2. SPLIT MODE (post-split in openwatch-public repository)
#    - HTTP calls to openwatch-core private service via CoreClient
#    - Uses split_ready_adapter.py for dual-mode access
#    - All endpoints apply PublicSignalSummary filtering automatically
#    - Sensitive internal fields are stripped (factors, weights, etc.)
#
# MIGRATION PATH POST-SPLIT:
# - CoreClient is automatically selected when CORE_SERVICE_URL is set
# - All adapters transparently switch to HTTP mode
# - PublicSignalSummary and PublicEntitySummary filtering is applied
# - Endpoint signatures remain UNCHANGED
#
# See: api/app/adapters/split_ready_adapter.py for dual-mode patterns
# See: shared/models/public_filter.py for PublicSignalSummary schema
#
# ═══════════════════════════════════════════════════════════════════════════════
# ── Public API response schemas (API contract — public layer) ─────────────────
from shared.models.coverage_v2 import (
    CoverageV2AnalyticsResponse,
    CoverageV2MapResponse,
    CoverageV2RunDetailResponse,
    CoverageV2SourcePreviewResponse,
    CoverageV2SourcesResponse,
    CoverageV2SummaryResponse,
    PublicSourcesResponse,
)
from shared.models.graph import (
    CaseGraphResponse,
    EntityPathResponse,
    NeighborhoodResponse,
    SignalGraphResponse,
)
from shared.models.public_filter import to_public_signal
from shared.models.radar import (
    RadarV2CaseListResponse,
    RadarV2CasePreviewResponse,
    RadarV2CoverageResponse,
    RadarV2SignalListResponse,
    RadarV2SignalPreviewResponse,
    RadarV2SummaryResponse,
)
from shared.models.signals import ContestationCreate, ContestationOut, SignalReplayOut

router = APIRouter()


@router.get("/coverage/v2/summary", response_model=CoverageV2SummaryResponse)
async def coverage_v2_summary(
    session: DbSession,
):
    return await get_coverage_v2_summary(session)


@router.get("/coverage/v2/sources", response_model=CoverageV2SourcesResponse)
async def coverage_v2_sources(
    session: DbSession,
    pagination: Pagination,
    status: str | None = Query(None, pattern="^(ok|warning|stale|error|pending)$"),
    domain: str | None = Query(None),
    enabled_only: bool = Query(False),
    q: str | None = Query(None),
    sort: str = Query("status_desc", pattern="^(status_desc|name_asc|freshness_desc|jobs_desc)$"),
):
    return await get_coverage_v2_sources(
        session,
        offset=pagination.offset,
        limit=pagination.limit,
        status=status,
        domain=domain,
        enabled_only=enabled_only,
        q=q,
        sort=sort,
    )


@router.get("/coverage/v2/source/{connector}/preview", response_model=CoverageV2SourcePreviewResponse)
async def coverage_v2_source_preview(
    connector: str,
    session: DbSession,
    runs_limit: int = Query(10, ge=3, le=50),
):
    preview = await get_coverage_v2_source_preview(
        session,
        connector=connector,
        runs_limit=runs_limit,
    )
    if preview is None:
        raise HTTPException(status_code=404, detail="Connector not found")
    return preview


@router.get("/coverage/v2/map", response_model=CoverageV2MapResponse)
async def coverage_v2_map(
    session: DbSession,
    layer: str = Query("uf", pattern="^(uf|municipio)$"),
    metric: str = Query("coverage", pattern="^(coverage|freshness|risk)$"),
):
    return await get_coverage_v2_map(session, layer=layer, metric=metric)


@router.get("/coverage/v2/analytics", response_model=CoverageV2AnalyticsResponse)
async def coverage_v2_analytics(session: DbSession):
    return await get_coverage_v2_analytics(session)


@router.get("/coverage/v2/run/{run_id}", response_model=CoverageV2RunDetailResponse)
async def coverage_v2_run_detail(
    run_id: uuid.UUID,
    session: DbSession,
):
    detail = await get_coverage_v2_run_detail(session, run_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return detail



@router.get("/sources", response_model=PublicSourcesResponse)
async def public_sources(session: DbSession):
    """Full transparency on data provenance — sources, veracity, whitelist."""
    return await get_public_sources(session)


@router.get("/radar/v2/summary", response_model=RadarV2SummaryResponse)
async def radar_v2_summary(
    session: DbSession,
    typology: str | None = Query(None, description="Filter by typology code (e.g. T01)"),
    severity: str | None = Query(None, description="Filter by severity"),
    period_from: datetime | None = Query(None, description="Filter: analysis period starts on or after this date"),
    period_to: datetime | None = Query(None, description="Filter: analysis period ends on or before this date"),
    corruption_type: str | None = Query(None, description="Filter by corruption type"),
    sphere: str | None = Query(None, description="Filter by sphere"),
):
    return await get_radar_v2_summary(
        session,
        typology_code=typology,
        severity=severity,
        period_from=period_from,
        period_to=period_to,
        corruption_type=corruption_type,
        sphere=sphere,
    )


@router.get("/radar/v2/signals", response_model=RadarV2SignalListResponse)
async def radar_v2_signals(
    session: DbSession,
    pagination: Pagination,
    typology: str | None = Query(None, description="Filter by typology code (e.g. T01)"),
    severity: str | None = Query(None, description="Filter by severity"),
    sort: str = Query("analysis_date", pattern="^(analysis_date|ingestion_date)$", description="Sort by analysis_date (period_end) or ingestion_date (created_at)"),
    period_from: datetime | None = Query(None, description="Filter: analysis period starts on or after this date"),
    period_to: datetime | None = Query(None, description="Filter: analysis period ends on or before this date"),
    corruption_type: str | None = Query(None, description="Filter by corruption type"),
    sphere: str | None = Query(None, description="Filter by sphere"),
):
    items, total = await get_radar_v2_signals(
        session,
        offset=pagination.offset,
        limit=pagination.limit,
        typology_code=typology,
        severity=severity,
        sort=sort,
        period_from=period_from,
        period_to=period_to,
        corruption_type=corruption_type,
        sphere=sphere,
    )
    return {
        "items": items,
        "total": total,
        "offset": pagination.offset,
        "limit": pagination.limit,
    }


@router.get("/radar/v2/cases", response_model=RadarV2CaseListResponse)
async def radar_v2_cases(
    session: DbSession,
    pagination: Pagination,
    typology: str | None = Query(None, description="Filter by typology code (e.g. T01)"),
    severity: str | None = Query(None, description="Filter by severity"),
    period_from: datetime | None = Query(None, description="Filter: analysis period starts on or after this date"),
    period_to: datetime | None = Query(None, description="Filter: analysis period ends on or before this date"),
    corruption_type: str | None = Query(None, description="Filter by corruption type"),
    sphere: str | None = Query(None, description="Filter by sphere"),
):
    items, total = await get_radar_v2_cases(
        session,
        offset=pagination.offset,
        limit=pagination.limit,
        typology_code=typology,
        severity=severity,
        period_from=period_from,
        period_to=period_to,
        corruption_type=corruption_type,
        sphere=sphere,
    )
    return {
        "items": items,
        "total": total,
        "offset": pagination.offset,
        "limit": pagination.limit,
    }


@router.get("/radar/v2/signal/{signal_id}/preview", response_model=RadarV2SignalPreviewResponse)
async def radar_v2_signal_preview(
    signal_id: uuid.UUID,
    session: DbSession,
    limit: int = Query(10, ge=1, le=30, description="Evidence preview limit"),
):
    preview = await get_radar_v2_signal_preview(session, signal_id=signal_id, evidence_limit=limit)
    if preview is None:
        raise HTTPException(status_code=404, detail="Signal not found")
    return preview


@router.get("/radar/v2/case/{case_id}/preview", response_model=RadarV2CasePreviewResponse)
async def radar_v2_case_preview(
    case_id: uuid.UUID,
    session: DbSession,
):
    preview = await get_radar_v2_case_preview(session, case_id=case_id)
    if preview is None:
        raise HTTPException(status_code=404, detail="Case not found")
    return preview


@router.post("/radar/v2/cases/batch-preview")
async def radar_v2_batch_preview(
    payload: dict,
    session: DbSession,
):
    """Batch case previews via the public gateway surface."""
    from contextlib import suppress

    case_ids_raw = payload.get("case_ids", [])
    if not case_ids_raw or len(case_ids_raw) > 50:
        raise HTTPException(status_code=400, detail="Provide 1-50 case_ids")

    case_ids: list[uuid.UUID] = []
    for cid in case_ids_raw:
        with suppress(ValueError, TypeError):
            case_ids.append(uuid.UUID(str(cid)))

    if not case_ids:
        return {"previews": {}}

    previews = {}
    for cid in case_ids:
        preview = await get_radar_v2_case_preview(session, case_id=cid)
        if preview is not None:
            previews[str(cid)] = preview

    return {"previews": previews}


@router.get("/radar/v2/coverage", response_model=RadarV2CoverageResponse)
async def radar_v2_coverage(session: DbSession):
    return await get_radar_v2_coverage(session)


@router.get("/case/{case_id}")
async def case_detail(case_id: uuid.UUID, session: DbSession):
    """Case detail with signals, explanation, and entity context."""
    case = await get_case_by_id(session, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    entities = await get_case_entities_with_roles(session, case_id)

    attrs = case.attrs or {}
    entity_names = attrs.get("entity_names", [])
    n_signals = len(case.items)

    # Collect unique typology labels from signals
    typology_names = sorted({
        item.signal.typology.name
        for item in case.items
        if item.signal.typology
    })

    # Build contextual explanation
    names_str = ", ".join(entity_names[:5])
    if len(entity_names) > 5:
        names_str += f" e mais {len(entity_names) - 5}"
    explanation = (
        f"Um caso consolidado agrupa sinais de risco que compartilham entidades em comum. "
        f"A analise automatica identificou que os {n_signals} sinais abaixo estao conectados"
    )
    if entity_names:
        explanation += f" por {len(entity_names)} entidade(s) ({names_str}) que aparecem em multiplas irregularidades potenciais."
    else:
        explanation += " por entidades que aparecem em multiplas irregularidades potenciais."

    signal_items = []
    for item in case.items:
        signal = item.signal
        signal_items.append(
            {
                "id": signal.id,
                "typology_code": signal.typology.code,
                "typology_name": signal.typology.name,
                "severity": signal.severity,
                "confidence": signal.confidence,
                "title": signal.title,
                "summary": signal.summary,
                "explanation_md": signal.explanation_md,
                "factors": signal.factors,
                "factor_descriptions": adapter_get_factor_descriptions(
                    signal.factors or {},
                    typology_code=signal.typology.code if signal.typology else None,
                ),
                "entity_count": len(signal.entity_ids or []),
                "evidence_count": len(signal.event_ids or []),
                "period_start": signal.period_start,
                "period_end": signal.period_end,
                "created_at": signal.created_at,
            }
        )

    return {
        "id": case.id,
        "title": case.title,
        "status": case.status,
        "severity": case.severity,
        "summary": case.summary,
        "case_type": case.case_type,
        "explanation": explanation,
        "entity_names": entity_names,
        "entities": [
            {
                "id": str(e["id"]),
                "name": e["name"],
                "type": e["type"],
                "cnpj_masked": e["cnpj_masked"],
                "roles": e["roles"],
                "signal_ids": e["signal_ids"],
            }
            for e in entities
        ],
        "typology_names": typology_names,
        "total_value_brl": attrs.get("total_value_brl"),
        "period_start": attrs.get("period_start"),
        "period_end": attrs.get("period_end"),
        "attrs": case.attrs,
        "created_at": case.created_at,
        "signals": signal_items,
    }


@router.get("/typology/{code}/legal-basis")
async def typology_legal_basis(code: str):
    """Legal basis metadata for a typology: laws, articles, violation types."""
    meta = adapter_get_typology_legal_metadata(code)
    if meta is None:
        raise HTTPException(status_code=404, detail="Typology not found")
    return {
        "typology_code": code.upper(),
        "corruption_types": meta.get("corruption_types", []),
        "spheres": meta.get("spheres", []),
        "evidence_level": meta.get("evidence_level"),
        "description_legal": meta.get("description_legal"),
        "law_articles": meta.get("law_articles", []),
    }


def _build_tipologia_item(typology_id: str, typology_name: str, meta: dict) -> dict:
    return {
        "code": typology_id,
        "name": typology_name,
        "corruption_types": meta.get("corruption_types", []),
        "spheres": meta.get("spheres", []),
        "evidence_level": meta.get("evidence_level", ""),
        "description_legal": meta.get("description_legal", ""),
        "law_articles": meta.get("law_articles", []),
    }


@router.get("/tipologia")
async def list_tipologias():
    """List all registered typologies with their legal metadata."""
    items = adapter_list_typologies()
    return {"typologies": items, "total": len(items)}


@router.get("/tipologia/{code}")
async def get_tipologia(code: str):
    """Metadata for a single typology by code (e.g. T03)."""
    result = adapter_get_typology(code)
    if result is None:
        raise HTTPException(status_code=404, detail="Typology not found")
    return result


@router.get("/case/{case_id}/legal-hypothesis")
async def case_legal_hypothesis(case_id: uuid.UUID, session: DbSession):
    """Legal violation hypotheses inferred for a case (served by openwatch-core)."""
    from api.app.adapters.core_adapter import _client
    result = await _client().get_case_legal_hypothesis(str(case_id))
    if result is None:
        return {"case_id": str(case_id), "hypotheses": []}
    return result


@router.get("/entity/search")
async def entity_search(
    session: DbSession,
    q: str = Query(..., min_length=2, description="Fuzzy name query (min 2 chars)"),
    type: str | None = Query(None, pattern="^(company|person)$", description="Filter by entity type"),
    limit: int = Query(20, ge=1, le=100, description="Max results (1-100)"),
):
    """Fuzzy entity search via pg_trgm. Person results are LGPD-scoped to public servants only. CPF is never returned."""
    results = await search_entities(session, q, entity_type=type, limit=limit)
    return results


@router.get("/entity/{entity_id}")
async def entity_detail(entity_id: uuid.UUID, session: DbSession):
    """Entity detail with identifiers, events, signals."""
    entity = await get_entity_by_id(session, entity_id)
    if entity is None:
        raise HTTPException(status_code=404, detail="Entity not found")
    return {
        "id": entity.id,
        "type": entity.type,
        "name": entity.name,
        "identifiers": {k: v for k, v in (entity.identifiers or {}).items() if k not in ("cpf", "cpf_hash")},
        "attrs": entity.attrs,
        "cluster_id": entity.cluster_id,
        "cluster_confidence": entity.cluster_confidence,
        "aliases": [
            {"type": a.alias_type, "value": a.value, "source": a.source}
            for a in entity.aliases
        ],
    }


@router.get("/org/{org_id}")
async def org_detail(org_id: uuid.UUID, session: DbSession):
    """Organization view — aggregated stats, risk distribution."""
    summary = await adapter_get_org_summary(session, org_id)
    if summary is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return summary


@router.get("/graph/neighborhood", response_model=NeighborhoodResponse)
async def graph_neighborhood(
    session: DbSession,
    entity_id: uuid.UUID = Query(..., description="Center entity ID"),
    depth: int = Query(1, ge=1, le=2, description="Traversal depth (1-2)"),
):
    """Graph neighborhood — nodes and edges around an entity (max 100 nodes)."""
    return await adapter_get_graph_neighborhood(session, entity_id, depth=depth, limit=100)


@router.get("/graph/path", response_model=EntityPathResponse)
async def get_graph_path(
    session: DbSession,
    from_id: uuid.UUID = Query(..., description="Source entity ID"),
    to_id: uuid.UUID = Query(..., description="Target entity ID"),
    max_hops: int = Query(5, ge=1, le=10, description="Maximum hops (1-10)"),
):
    """Shortest path between two entities via recursive CTE with temporal annotations."""
    if from_id == to_id:
        raise HTTPException(status_code=422, detail="from_id and to_id must be different entities")
    return await adapter_get_entity_path(session, from_id, to_id, max_hops)


@router.get("/case/{case_id}/graph", response_model=CaseGraphResponse)
async def case_graph(
    case_id: uuid.UUID,
    session: DbSession,
    depth: int = Query(1, ge=0, le=2, description="Traversal depth (0=seed-only, 1-2=BFS expansion)"),
    focus_signal_id: uuid.UUID | None = Query(
        None,
        description="Optional signal id to highlight entities/edges linked to one signal",
    ),
):
    """Case investigation graph — all entities from case signals + optional BFS neighborhood."""
    result = await get_case_graph(
        session,
        case_id,
        depth=depth,
        limit=300,
        focus_signal_id=focus_signal_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Case not found")
    return result


@router.get("/signal/{signal_id}/graph", response_model=SignalGraphResponse)
async def signal_graph(
    signal_id: uuid.UUID,
    session: DbSession,
):
    """Signal investigation graph — narrative + timeline + explainable edges."""
    result = await get_signal_graph(session, signal_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Signal not found")
    return result


@router.get("/compare/prices")
async def compare_prices(
    session: DbSession,
    catmat_code: str | None = Query(None),
    description: str | None = Query(None),
):
    """Price comparison — baseline stats, outlier highlights."""
    if not catmat_code:
        return {
            "catmat_code": catmat_code,
            "description": description,
            "baseline": None,
            "items": [],
        }

    # "PRICE_BY_ITEM" is the baseline type key — a public constant, not a protected enum
    scope_key = f"catmat_group::{catmat_code}"
    baseline = await adapter_get_baseline(
        session,
        "PRICE_BY_ITEM",
        scope_key,
    )

    return {
        "catmat_code": catmat_code,
        "description": description,
        "baseline": baseline,
        "items": [],
    }


@router.get("/signal/{signal_id}")
async def signal_detail(signal_id: uuid.UUID, session: DbSession):
    """
    Signal detail with typology, factors, evidence, and associated case.
    
    POST-SPLIT: This endpoint will use CoreClient and apply PublicSignalSummary filtering.
    See split_ready_adapter.py for dual-mode implementation pattern.
    """
    detail = await adapter_get_signal_detail(session, signal_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Signal not found")
    
    # SPLIT-READY: Filter sensitive internal fields for public API
    # In split mode, CoreClient will handle this automatically
    if isinstance(detail, dict):
        # Apply public filter if response is dict (monorepo mode)
        filtered = to_public_signal(detail) if detail.get("typology_code") else detail
        return filtered if filtered else detail
    return detail


@router.get("/signal/{signal_id}/evidence")
async def signal_evidence(
    signal_id: uuid.UUID,
    session: DbSession,
    pagination: Pagination,
    sort: str = Query(
        "occurred_at_desc",
        pattern="^(occurred_at_desc|occurred_at_asc|value_desc|value_asc)$",
    ),
):
    """Paginated evidence list based on all event_ids linked to the signal."""
    page = await get_signal_evidence_page(
        session,
        signal_id=signal_id,
        offset=pagination.offset,
        limit=pagination.limit,
        sort=sort,
    )
    if page is None:
        raise HTTPException(status_code=404, detail="Signal not found")
    return page


@router.get("/signal/{signal_id}/related")
async def signal_related(signal_id: uuid.UUID, session: DbSession):
    """Related signals that share at least one entity with the given signal."""
    signal = await adapter_get_signal_by_id(session, signal_id)
    if signal is None:
        raise HTTPException(status_code=404, detail="Signal not found")

    signal_entity_ids = signal.entity_ids or []
    if not signal_entity_ids:
        return []

    # SQL: find signals that share at least one entity_id via JSONB overlap
    from sqlalchemy import text

    entity_id_strs = [str(e) for e in signal_entity_ids]
    overlap_stmt = text("""
        SELECT rs.id, rs.severity, rs.confidence, rs.title, rs.created_at,
               t.code AS typology_code, t.name AS typology_name
        FROM risk_signal rs
        LEFT JOIN typology t ON t.id = rs.typology_id
        WHERE rs.id != :signal_id
          AND EXISTS (
              SELECT 1
              FROM jsonb_array_elements_text(rs.entity_ids) AS eid
              WHERE eid = ANY(:entity_ids)
          )
        ORDER BY rs.created_at DESC
        LIMIT 5
    """)
    result = await session.execute(
        overlap_stmt,
        {"signal_id": signal_id, "entity_ids": entity_id_strs},
    )
    related = result.all()

    return [
        {
            "id": r.id,
            "typology_code": r.typology_code,
            "typology_name": r.typology_name,
            "title": r.title,
            "severity": r.severity,
            "confidence": r.confidence,
            "created_at": r.created_at,
        }
        for r in related
    ]


@router.get("/signals/{signal_id}/evidence/export")
async def export_signal_evidence(
    signal_id: uuid.UUID,
    session: DbSession,
    format: str = Query("json", pattern="^(json|csv)$"),
):
    signal = await adapter_get_signal_by_id(session, signal_id)
    if signal is None:
        raise HTTPException(status_code=404, detail="Signal not found")

    package = None
    if signal.evidence_package_id:
        package = await adapter_get_evidence_package_by_id(session, signal.evidence_package_id)

    payload = {
        "signal_id": str(signal.id),
        "typology_code": signal.typology.code if signal.typology else None,
        "title": signal.title,
        "severity": signal.severity,
        "confidence": signal.confidence,
        "completeness_score": signal.completeness_score,
        "completeness_status": signal.completeness_status,
        "evidence_refs": signal.evidence_refs or [],
        "evidence_package": (
            {
                "id": str(package.id),
                "source_url": package.source_url,
                "source_hash": package.source_hash,
                "captured_at": package.captured_at.isoformat() if package.captured_at else None,
                "parser_version": package.parser_version,
                "model_version": package.model_version,
                "raw_snapshot_uri": package.raw_snapshot_uri,
                "normalized_snapshot_uri": package.normalized_snapshot_uri,
                "signature": package.signature,
            }
            if package
            else None
        ),
    }

    if format == "json":
        return payload

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "signal_id",
            "typology_code",
            "title",
            "severity",
            "confidence",
            "completeness_score",
            "completeness_status",
            "ref_type",
            "ref_id",
            "url",
            "source_hash",
            "captured_at",
            "description",
        ]
    )
    refs = signal.evidence_refs or []
    if not refs:
        writer.writerow(
            [
                str(signal.id),
                signal.typology.code if signal.typology else "",
                signal.title,
                signal.severity,
                signal.confidence,
                signal.completeness_score,
                signal.completeness_status,
                "",
                "",
                "",
                package.source_hash if package else "",
                package.captured_at.isoformat() if package and package.captured_at else "",
                "",
            ]
        )
    for ref in refs:
        writer.writerow(
            [
                str(signal.id),
                signal.typology.code if signal.typology else "",
                signal.title,
                signal.severity,
                signal.confidence,
                signal.completeness_score,
                signal.completeness_status,
                ref.get("ref_type", ""),
                ref.get("ref_id", ""),
                ref.get("url", ""),
                ref.get("source_hash", package.source_hash if package else ""),
                ref.get(
                    "captured_at",
                    package.captured_at.isoformat() if package and package.captured_at else "",
                ),
                ref.get("description", ""),
            ]
        )

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="signal-evidence-{signal_id}.csv"',
        },
    )


@router.post("/signals/{signal_id}/replay", response_model=SignalReplayOut)
async def replay_signal_endpoint(signal_id: uuid.UUID, session: DbSession):
    replay = await adapter_replay_signal(session, signal_id)
    if replay is None:
        raise HTTPException(status_code=404, detail="Signal not found")
    return replay


@router.get("/signal/{signal_id}/provenance")
async def signal_provenance(signal_id: uuid.UUID, session: DbSession):
    """Full provenance chain: Signal -> Events -> RawSources."""
    signal = await adapter_get_signal_by_id(session, signal_id)
    if signal is None:
        raise HTTPException(status_code=404, detail="Signal not found")
    event_ids = []
    from contextlib import suppress
    for eid_str in (signal.event_ids or []):
        with suppress(ValueError, TypeError):
            event_ids.append(uuid.UUID(str(eid_str)))
    event_raw_sources = await adapter_get_signal_provenance(session, signal_id)
    return {
        "signal_id": signal.id,
        "title": signal.title,
        "typology_code": signal.typology.code if signal.typology else None,
        "events": [
            {
                "event_id": eid,
                "raw_sources": [
                    {
                        "id": rs.id,
                        "connector": rs.connector,
                        "job": rs.job,
                        "raw_id": rs.raw_id,
                        "raw_data": rs.raw_data,
                        "created_at": rs.created_at,
                    }
                    for rs in sources
                ],
            }
            for eid, sources in event_raw_sources.items()
        ],
    }


@router.get("/event/{event_id}/raw-sources")
async def event_raw_sources_endpoint(event_id: uuid.UUID, session: DbSession):
    """Original API JSON for one event."""
    raw_sources = await adapter_get_signal_provenance(session, event_id)
    return {
        "event_id": event_id,
        "raw_sources": [
            {
                "id": rs.id,
                "connector": rs.connector,
                "job": rs.job,
                "raw_id": rs.raw_id,
                "raw_data": rs.raw_data,
                "created_at": rs.created_at,
            }
            for rs in raw_sources
        ],
    }


@router.get("/case/{case_id}/provenance")
async def case_provenance(case_id: uuid.UUID, session: DbSession):
    """Complete investigative web with raw data for a case."""
    result = await adapter_get_case_provenance(session, case_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Case not found")
    return result


@router.get("/case/{case_id}/related")
async def case_related(case_id: uuid.UUID, session: DbSession):
    """Related cases that share at least one entity name with the given case."""
    case = await get_case_by_id(session, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")

    entity_name_set = list((case.attrs or {}).get("entity_names", []))
    if not entity_name_set:
        return []

    # SQL: find cases whose attrs->'entity_names' overlaps with this case's entity names
    from sqlalchemy import text

    related_stmt = text("""
        SELECT c.id, c.title, c.severity, c.case_type, c.attrs, c.created_at
        FROM "case" c,
        LATERAL jsonb_array_elements_text(COALESCE(c.attrs->'entity_names', '[]'::jsonb)) AS name
        WHERE c.id != :case_id
          AND name = ANY(:entity_names)
        GROUP BY c.id, c.title, c.severity, c.case_type, c.attrs, c.created_at
        ORDER BY c.created_at DESC
        LIMIT 3
    """)
    result = await session.execute(
        related_stmt,
        {"case_id": case_id, "entity_names": entity_name_set},
    )
    rows = result.all()

    return [
        {
            "id": r.id,
            "title": r.title,
            "severity": r.severity,
            "case_type": r.case_type,
            "signal_count": (r.attrs or {}).get("signal_count") if r.attrs else None,
            "created_at": r.created_at,
        }
        for r in rows
    ]


@router.get("/case/{case_id}/dossier-summary")
async def case_dossier_summary(case_id: uuid.UUID, session: DbSession):
    """Full dossier summary — one call replaces case preview + legal + related."""
    result = await get_dossier_summary(session, case_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Case not found")
    return result


@router.get("/case/{case_id}/dossier-timeline")
async def case_dossier_timeline(case_id: uuid.UUID, session: DbSession):
    """Full timeline data for a case dossier — events, participants, signals, entities."""
    result = await get_dossier_timeline(session, case_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Case not found")
    return result


def _contestation_out(c: Contestation) -> ContestationOut:
    return ContestationOut(
        id=c.id,
        signal_id=c.signal_id,
        entity_id=c.entity_id,
        report_type=c.report_type,
        evidence_url=c.evidence_url,
        status=c.status,
        requester_name=c.requester_name,
        requester_email=c.requester_email,
        reason=c.reason,
        details=c.details,
        resolution=c.resolution,
        resolved_at=c.resolved_at,
        created_at=c.created_at,
    )


def _build_contestation(payload: ContestationCreate) -> Contestation:
    if payload.signal_id is None and payload.entity_id is None:
        raise HTTPException(
            status_code=422,
            detail="Either signal_id or entity_id must be provided",
        )
    return Contestation(
        signal_id=payload.signal_id,
        entity_id=payload.entity_id,
        report_type=payload.report_type,
        evidence_url=payload.evidence_url,
        requester_name=payload.requester_name,
        requester_email=payload.requester_email,
        reason=payload.reason,
        details=payload.details,
        status="open",
    )


@router.post("/contestation", response_model=ContestationOut, status_code=status.HTTP_201_CREATED)
async def create_contestation(payload: ContestationCreate, session: DbSession):
    contestation = _build_contestation(payload)
    session.add(contestation)
    await session.commit()
    await session.refresh(contestation)
    return _contestation_out(contestation)


@router.post("/contestations", response_model=ContestationOut, status_code=status.HTTP_201_CREATED)
async def create_contestation_v2(payload: ContestationCreate, session: DbSession):
    """Submit an error report for a signal or entity."""
    contestation = _build_contestation(payload)
    session.add(contestation)
    await session.commit()
    await session.refresh(contestation)
    return _contestation_out(contestation)


@router.get("/contestation/{contestation_id}", response_model=ContestationOut)
async def get_contestation(contestation_id: uuid.UUID, session: DbSession):
    contestation = await session.get(Contestation, contestation_id)
    if contestation is None:
        raise HTTPException(status_code=404, detail="Contestation not found")
    return _contestation_out(contestation)
