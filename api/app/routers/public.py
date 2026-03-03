import uuid
import csv
from datetime import datetime
from io import StringIO
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Response, status

from api.app.deps import DbSession, Pagination
from shared.models.coverage_v2 import (
    CoverageV2AnalyticsResponse,
    CoverageV2MapResponse,
    CoverageV2RunDetailResponse,
    CoverageV2SourcePreviewResponse,
    CoverageV2SourcesResponse,
    CoverageV2SummaryResponse,
)
from shared.models.graph import CaseGraphResponse, NeighborhoodResponse, SignalGraphResponse
from shared.models.orm import Contestation
from shared.models.radar import (
    RadarV2CaseListResponse,
    RadarV2CasePreviewResponse,
    RadarV2CoverageResponse,
    RadarV2SignalListResponse,
    RadarV2SignalPreviewResponse,
    RadarV2SummaryResponse,
)
from shared.models.signals import ContestationCreate, ContestationOut, SignalReplayOut
from shared.repo.queries import (
    get_case_by_id,
    get_case_graph,
    get_coverage_v2_analytics,
    get_coverage_v2_map,
    get_coverage_v2_run_detail,
    get_coverage_v2_source_preview,
    get_coverage_v2_sources,
    get_coverage_v2_summary,
    get_evidence_package_by_id,
    get_entity_by_id,
    get_graph_neighborhood,
    get_org_summary,
    get_radar_v2_case_preview,
    get_radar_v2_cases,
    get_radar_v2_coverage,
    get_radar_v2_signal_preview,
    get_radar_v2_signals,
    get_radar_v2_summary,
    get_signal_by_id,
    get_signal_detail,
    get_signal_graph,
    get_signal_evidence_page,
    replay_signal,
)

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
    status: Optional[str] = Query(None, pattern="^(ok|warning|stale|error|pending)$"),
    domain: Optional[str] = Query(None),
    enabled_only: bool = Query(False),
    q: Optional[str] = Query(None),
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



@router.get("/radar/v2/summary", response_model=RadarV2SummaryResponse)
async def radar_v2_summary(
    session: DbSession,
    typology: Optional[str] = Query(None, description="Filter by typology code (e.g. T01)"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    period_from: Optional[datetime] = Query(None, description="Filter: analysis period starts on or after this date"),
    period_to: Optional[datetime] = Query(None, description="Filter: analysis period ends on or before this date"),
    corruption_type: Optional[str] = Query(None, description="Filter by corruption type"),
    sphere: Optional[str] = Query(None, description="Filter by sphere"),
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
    typology: Optional[str] = Query(None, description="Filter by typology code (e.g. T01)"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    sort: str = Query("analysis_date", pattern="^(analysis_date|ingestion_date)$", description="Sort by analysis_date (period_end) or ingestion_date (created_at)"),
    period_from: Optional[datetime] = Query(None, description="Filter: analysis period starts on or after this date"),
    period_to: Optional[datetime] = Query(None, description="Filter: analysis period ends on or before this date"),
    corruption_type: Optional[str] = Query(None, description="Filter by corruption type"),
    sphere: Optional[str] = Query(None, description="Filter by sphere"),
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
    typology: Optional[str] = Query(None, description="Filter by typology code (e.g. T01)"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    period_from: Optional[datetime] = Query(None, description="Filter: analysis period starts on or after this date"),
    period_to: Optional[datetime] = Query(None, description="Filter: analysis period ends on or before this date"),
    corruption_type: Optional[str] = Query(None, description="Filter by corruption type"),
    sphere: Optional[str] = Query(None, description="Filter by sphere"),
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


@router.get("/radar/v2/coverage", response_model=RadarV2CoverageResponse)
async def radar_v2_coverage(session: DbSession):
    return await get_radar_v2_coverage(session)


@router.get("/case/{case_id}")
async def case_detail(case_id: uuid.UUID, session: DbSession):
    """Case detail with signals, explanation, and entity context."""
    case = await get_case_by_id(session, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")

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

    from shared.typologies.factor_metadata import get_factor_descriptions

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
                "factor_descriptions": get_factor_descriptions(
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
        "explanation": explanation,
        "entity_names": entity_names,
        "typology_names": typology_names,
        "total_value_brl": attrs.get("total_value_brl"),
        "period_start": attrs.get("period_start"),
        "period_end": attrs.get("period_end"),
        "attrs": case.attrs,
        "created_at": case.created_at,
        "signals": signal_items,
    }


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
        "identifiers": entity.identifiers,
        "attrs": entity.attrs,
        "cluster_id": entity.cluster_id,
        "aliases": [
            {"type": a.alias_type, "value": a.value, "source": a.source}
            for a in entity.aliases
        ],
    }


@router.get("/org/{org_id}")
async def org_detail(org_id: uuid.UUID, session: DbSession):
    """Organization view — aggregated stats, risk distribution."""
    summary = await get_org_summary(session, org_id)
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
    return await get_graph_neighborhood(session, entity_id, depth=depth, limit=100)


@router.get("/case/{case_id}/graph", response_model=CaseGraphResponse)
async def case_graph(
    case_id: uuid.UUID,
    session: DbSession,
    depth: int = Query(1, ge=1, le=2, description="Traversal depth (1-2)"),
    focus_signal_id: Optional[uuid.UUID] = Query(
        None,
        description="Optional signal id to highlight entities/edges linked to one signal",
    ),
):
    """Case investigation graph — all entities from case signals + BFS neighborhood."""
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
    catmat_code: Optional[str] = Query(None),
    description: Optional[str] = Query(None),
):
    """Price comparison — baseline stats, outlier highlights."""
    from shared.baselines.models import BaselineType
    from shared.repo.queries import get_baseline

    if not catmat_code:
        return {
            "catmat_code": catmat_code,
            "description": description,
            "baseline": None,
            "items": [],
        }

    scope_key = f"catmat_group::{catmat_code}"
    baseline = await get_baseline(
        session,
        BaselineType.PRICE_BY_ITEM.value,
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
    """Signal detail with typology, factors, evidence, and associated case."""
    detail = await get_signal_detail(session, signal_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Signal not found")
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


@router.get("/signals/{signal_id}/evidence/export")
async def export_signal_evidence(
    signal_id: uuid.UUID,
    session: DbSession,
    format: str = Query("json", pattern="^(json|csv)$"),
):
    signal = await get_signal_by_id(session, signal_id)
    if signal is None:
        raise HTTPException(status_code=404, detail="Signal not found")

    package = None
    if signal.evidence_package_id:
        package = await get_evidence_package_by_id(session, signal.evidence_package_id)

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
    replay = await replay_signal(session, signal_id)
    if replay is None:
        raise HTTPException(status_code=404, detail="Signal not found")
    return replay


@router.post("/contestation", response_model=ContestationOut, status_code=status.HTTP_201_CREATED)
async def create_contestation(payload: ContestationCreate, session: DbSession):
    contestation = Contestation(
        signal_id=payload.signal_id,
        requester_name=payload.requester_name,
        requester_email=payload.requester_email,
        reason=payload.reason,
        details=payload.details,
        status="open",
    )
    session.add(contestation)
    await session.commit()
    await session.refresh(contestation)

    return ContestationOut(
        id=contestation.id,
        signal_id=contestation.signal_id,
        status=contestation.status,
        requester_name=contestation.requester_name,
        requester_email=contestation.requester_email,
        reason=contestation.reason,
        details=contestation.details,
        resolution=contestation.resolution,
        resolved_at=contestation.resolved_at,
        created_at=contestation.created_at,
    )


@router.get("/contestation/{contestation_id}", response_model=ContestationOut)
async def get_contestation(contestation_id: uuid.UUID, session: DbSession):
    contestation = await session.get(Contestation, contestation_id)
    if contestation is None:
        raise HTTPException(status_code=404, detail="Contestation not found")

    return ContestationOut(
        id=contestation.id,
        signal_id=contestation.signal_id,
        status=contestation.status,
        requester_name=contestation.requester_name,
        requester_email=contestation.requester_email,
        reason=contestation.reason,
        details=contestation.details,
        resolution=contestation.resolution,
        resolved_at=contestation.resolved_at,
        created_at=contestation.created_at,
    )
