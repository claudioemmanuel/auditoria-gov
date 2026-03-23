import hashlib
import json
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shared.models.orm import (
    BaselineSnapshot,
    Case,
    CaseItem,
    CoverageRegistry,
    ERRunState,
    Entity,
    Event,
    EventParticipant,
    EvidencePackage,
    GraphEdge,
    GraphNode,
    RawRun,
    RawSource,
    RiskSignal,
    SignalEntity,
    Typology,
    TypologyRunLog,
)
from shared.models.coverage import CoverageItem, CoverageMapItem, CoverageMapResponse
from shared.models.coverage_v2 import (
    CoverageV2AnalyticsResponse,
    CoverageV2AnalyticsSummary,
    CoverageV2LatestRun,
    CoverageV2MapNational,
    CoverageV2MapResponse,
    CoverageV2PipelineStage,
    CoverageV2PipelineSummary,
    CoverageV2RunDetailResponse,
    CoverageV2RunFieldProfile,
    CoverageV2RunSampleRecord,
    CoverageV2RuntimeTotals,
    CoverageV2ScheduleWindow,
    CoverageV2SourceItem,
    CoverageV2SourcePreviewConnector,
    CoverageV2SourcePreviewJob,
    CoverageV2SourcePreviewResponse,
    CoverageV2SourceRuntime,
    CoverageV2SourcesResponse,
    CoverageV2StatusCounts,
    CoverageV2SummaryResponse,
    CoverageV2Totals,
)
from shared.models.graph import (
    CaseFocusSignalSummary,
    CaseGraphResponse,
    CaseSignalBrief,
    ClusterEntityOut,
    CoParticipantOut,
    EntityPathResponse,
    ExpandedNodeOut,
    ExpansionEdgeOut,
    GraphDiagnosticsOut,
    GraphEdgeOut,
    GraphNodeOut,
    NeighborhoodResponse,
    PathHopOut,
    SignalGraphDiagnosticsOut,
    SignalGraphEdgeOut,
    SignalGraphNodeOut,
    SignalGraphOverviewOut,
    SignalGraphResponse,
    SignalGraphSignalOut,
    SignalInvolvedEntityProfileOut,
    SignalInvolvedEntityRoleOut,
    SignalPatternStoryOut,
    SignalStoryActorOut,
    SignalTimelineEventOut,
    SignalTimelineParticipantOut,
    VirtualCenterNodeOut,
)
from shared.models.signals import (
    EvidenceRef,
    RefType,
    RiskSignalOut,
    SignalReplayOut,
    SignalSeverity,
)
from shared.models.radar import (
    RadarV2CaseListItemOut,
    RadarV2CoverageResponse,
    RadarV2CoverageSummaryOut,
    RadarV2SeverityCountsOut,
    RadarV2SignalListItemOut,
    RadarV2SummaryResponse,
    RadarV2TotalsOut,
    RadarV2TypologyCountOut,
)
# NOTE: Do NOT import from shared.typologies at module level — it causes a
# circular import (typology implementations import queries.py).  Use lazy
# imports inside the functions that need factor_metadata helpers.


_SEVERITY_TO_SCORE = {
    "low": 0.25,
    "medium": 0.5,
    "high": 0.75,
    "critical": 1.0,
}

_MISSING_TEXT_SENTINELS = {
    "",
    "unknown",
    "sem classificacao",
    "sem classificação",
    "null",
    "none",
    "n/a",
    "na",
    "nao_informado",
    "não informado",
}

_ROLE_LABELS = {
    "buyer": "Orgao comprador",
    "procuring_entity": "Entidade contratante",
    "supplier": "Fornecedor",
    "winner": "Vencedor",
    "bidder": "Licitante",
    "sanctioned": "Entidade sancionada",
}

_INITIATOR_ROLES = {
    "buyer",
    "procuring_entity",
    "contracting_authority",
    "orgao",
    "senador",
    "deputado",
}

_TARGET_ROLES = {
    "supplier",
    "winner",
    "fornecedor",
    "beneficiario",
    "payee",
}

_TYPOLOGY_LEGAL_REFERENCES = {
    "T03": "Lei 14.133/2021 (dispensa de licitacao por valor)",
}

_COVERAGE_STATUS_RANK = {
    "error": 5,
    "stale": 4,
    "warning": 3,
    "pending": 2,
    "ok": 1,
}

_COVERAGE_PROFILE_SAMPLE_LIMIT = 200
_COVERAGE_RECORD_SAMPLE_LIMIT = 12
_COVERAGE_MAX_RAW_DATA_CHARS = 2400
_COVERAGE_MAX_PREVIEW_VALUE_CHARS = 160
_COVERAGE_STUCK_MINUTES = 120

_COVERAGE_PREVIEW_KEYS = (
    "id",
    "numero",
    "codigoEmenda",
    "numeroEmenda",
    "objeto",
    "orgao_nome",
    "fornecedor_nome",
    "autor",
    "nomeAutor",
    "tipoEmenda",
    "valor_global",
    "valorPago",
    "data_assinatura",
    "dataInicioSancao",
    "dataFimSancao",
    "dataPublicacaoSancao",
    "sancionado",
    "pessoa",
)


def _normalize_missing_text(value: object, fallback: str = "nao_informado") -> str:
    text = str(value or "").strip()
    if not text:
        return fallback
    if text.lower() in _MISSING_TEXT_SENTINELS:
        return fallback
    return text


def _display_missing_text(value: object) -> str:
    normalized = _normalize_missing_text(value)
    if normalized == "nao_informado":
        return "Nao informado pela fonte"
    return normalized


def _to_uuid_list(raw_values: list[object] | None) -> list[uuid.UUID]:
    parsed: list[uuid.UUID] = []
    for raw in raw_values or []:
        try:
            parsed.append(uuid.UUID(str(raw)))
        except (ValueError, TypeError):
            continue
    return parsed


def _role_label(role_code: str) -> str:
    return _ROLE_LABELS.get(role_code, role_code.replace("_", " ").capitalize())


def _edge_label_for_roles(source_role: str, target_role: str) -> str:
    source = source_role.lower()
    target = target_role.lower()
    if source in {"buyer", "procuring_entity"} and target in {"supplier", "winner", "fornecedor"}:
        return "Relacao de compra/fornecimento"
    if source in {"senador", "deputado"} and target in {"supplier", "fornecedor", "beneficiario"}:
        return "Relacao entre agente publico e favorecido"
    return f"{_role_label(source_role)} -> {_role_label(target_role)}"


def _event_sort_key(event: Event) -> datetime:
    return event.occurred_at or datetime.max.replace(tzinfo=timezone.utc)


def _extract_photo_url(attrs: dict | None) -> str | None:
    source = attrs or {}
    for key in (
        "url_foto",
        "urlFoto",
        "photo_url",
        "foto_url",
        "UrlFotoParlamentar",
    ):
        value = source.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _actor_sort_key(actor: SignalStoryActorOut) -> tuple[int, int, str]:
    has_name = 0 if actor.name.strip() else 1  # nameless actors sort last
    return (-actor.event_count, has_name, actor.name.lower())


def _coverage_now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _coverage_is_stuck_run(run: RawRun, now: datetime | None = None) -> bool:
    now_ref = now or _coverage_now_utc()
    if run.status != "running" or run.created_at is None:
        return False
    started_at = run.created_at
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=timezone.utc)
    return (now_ref - started_at) > timedelta(minutes=_COVERAGE_STUCK_MINUTES)


def _coverage_empty_status_counts() -> dict[str, int]:
    return {"ok": 0, "warning": 0, "stale": 0, "error": 0, "pending": 0}


def _coverage_worst_status(counts: dict[str, int]) -> str:
    status = "ok"
    rank = -1
    for key, value in counts.items():
        if value <= 0:
            continue
        current_rank = _COVERAGE_STATUS_RANK.get(key, 0)
        if current_rank > rank:
            status = key
            rank = current_rank
    return status


def _coverage_connector_label(connector: str) -> str:
    return connector.replace("_", " ")


def _coverage_safe_iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt else None


def _coverage_value_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def _coverage_compact_nested(value: Any) -> Any:
    if isinstance(value, dict):
        preferred_subkeys = (
            "id",
            "nome",
            "codigoFormatado",
            "descricaoPortal",
            "descricaoResumida",
            "cnpjFormatado",
            "cpfFormatado",
        )
        compact = {k: value[k] for k in preferred_subkeys if k in value}
        if compact:
            return compact
        keys = list(value.keys())[:4]
        return {k: value[k] for k in keys}
    if isinstance(value, list):
        first = value[0] if value else None
        return {"items": len(value), "first": _coverage_compact_nested(first)}
    if isinstance(value, str) and len(value) > _COVERAGE_MAX_PREVIEW_VALUE_CHARS:
        return f"{value[:_COVERAGE_MAX_PREVIEW_VALUE_CHARS]}..."
    return value


def _coverage_preview_value(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return _coverage_compact_nested(value)
    if isinstance(value, str):
        if len(value) <= _COVERAGE_MAX_PREVIEW_VALUE_CHARS:
            return value
        return f"{value[:_COVERAGE_MAX_PREVIEW_VALUE_CHARS]}..."
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    text = json.dumps(value, ensure_ascii=False, default=str)
    if len(text) <= _COVERAGE_MAX_PREVIEW_VALUE_CHARS:
        return text
    return f"{text[:_COVERAGE_MAX_PREVIEW_VALUE_CHARS]}..."


def _coverage_example_fingerprint(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    except TypeError:
        return str(value)


def _coverage_build_preview(raw_data: dict[str, Any]) -> dict[str, Any]:
    keys = [key for key in _COVERAGE_PREVIEW_KEYS if key in raw_data]
    if len(keys) < 8:
        for key in raw_data.keys():
            if key not in keys:
                keys.append(key)
            if len(keys) >= 8:
                break
    return {key: _coverage_compact_nested(raw_data.get(key)) for key in keys}


def _coverage_trim_raw_data(raw_data: dict[str, Any]) -> dict[str, Any]:
    text = str(raw_data)
    if len(text) <= _COVERAGE_MAX_RAW_DATA_CHARS:
        return raw_data
    trimmed: dict[str, Any] = {}
    for key, value in raw_data.items():
        if len(str(trimmed)) > _COVERAGE_MAX_RAW_DATA_CHARS:
            break
        trimmed[key] = _coverage_compact_nested(value)
    trimmed["_truncated"] = True
    trimmed["_note"] = "Payload reduzido para visualizacao."
    return trimmed


def _coverage_run_error_message(run: RawRun) -> Optional[str]:
    if not run.errors:
        return None
    if isinstance(run.errors, dict):
        # Yielded runs store operational metadata, not errors.
        if run.errors.get("yielded"):
            return None
        for key in ("message", "error", "detail"):
            value = run.errors.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return str(run.errors)


def _parse_cursor_info(cursor: str | None) -> tuple[str | None, int | None, int | None]:
    """Parse cursor like 'w3p500' or 'd2w3p500' into human-readable info."""
    if not cursor:
        return None, None, None
    import re
    m = re.match(r"(?:d(\d+))?w(\d+)p(\d+)", cursor)
    if m:
        dim, window_idx, page = m.group(1), int(m.group(2)), int(m.group(3))
        prefix = f"Dim {dim}, " if dim else ""
        label = f"{prefix}Janela {window_idx + 1}, Pag {page}"
        return label, window_idx, page
    if cursor.isdigit():
        return f"Pag {cursor}", None, int(cursor)
    return None, None, None


def _coverage_latest_run_to_model(run: RawRun, now: datetime) -> CoverageV2LatestRun:
    elapsed_seconds = None
    progress_pct = None
    pages_fetched = None
    rate_per_min = None
    cursor_info = None

    if run.status == "running" and run.created_at:
        elapsed_seconds = round((now - run.created_at).total_seconds(), 1)

    if run.items_fetched and run.items_normalized:
        progress_pct = round((run.items_normalized / max(run.items_fetched, 1)) * 100, 1)

    # Extract progress metadata from _progress key in errors JSONB
    if run.errors and isinstance(run.errors, dict):
        pm = run.errors.get("_progress")
        if pm and isinstance(pm, dict):
            pages_fetched = pm.get("pages")
            rate_per_min = pm.get("rate_per_min")

    # Parse cursor for human-readable position
    label, _win_idx, _page = _parse_cursor_info(run.cursor_end)
    if label:
        cursor_info = label

    # For completed/yielded, fetch is done — normalize progress is what matters
    fetch_progress_pct = 100.0 if run.status in ("completed", "yielded") else None

    return CoverageV2LatestRun(
        id=run.id,
        status=run.status,
        is_stuck=_coverage_is_stuck_run(run, now),
        started_at=run.created_at,
        finished_at=run.finished_at,
        items_fetched=run.items_fetched or 0,
        items_normalized=run.items_normalized or 0,
        error_message=_coverage_run_error_message(run),
        elapsed_seconds=elapsed_seconds,
        progress_pct=progress_pct,
        fetch_progress_pct=fetch_progress_pct,
        pages_fetched=pages_fetched,
        rate_per_min=rate_per_min,
        cursor_info=cursor_info,
    )


def _coverage_scalar_one_or_none(result):
    if hasattr(result, "scalar_one_or_none"):
        return result.scalar_one_or_none()
    if hasattr(result, "scalars"):
        rows = result.scalars().all()
        return rows[0] if rows else None
    rows = result.all() if hasattr(result, "all") else []
    return rows[0] if rows else None


def _coverage_scalar_one(result, default=0):
    if hasattr(result, "scalar_one"):
        value = result.scalar_one()
        return default if value is None else value
    row = _coverage_scalar_one_or_none(result)
    if row is None:
        return default
    return row


def _coverage_row_one_or_none(result):
    if hasattr(result, "one_or_none"):
        return result.one_or_none()
    rows = result.all() if hasattr(result, "all") else []
    return rows[0] if rows else None


def _coverage_build_job_info(connector_name: str, job_name: str) -> dict[str, Any]:
    from shared.connectors import get_connector

    info: dict[str, Any] = {
        "connector": connector_name,
        "job": job_name,
        "description": None,
        "domain": None,
        "supports_incremental": None,
        "enabled": None,
        "default_params": {},
    }
    try:
        connector = get_connector(connector_name)
        job_spec = next((job for job in connector.list_jobs() if job.name == job_name), None)
        if job_spec is not None:
            info.update(
                {
                    "description": job_spec.description,
                    "domain": job_spec.domain,
                    "supports_incremental": job_spec.supports_incremental,
                    "enabled": job_spec.enabled,
                    "default_params": job_spec.default_params or {},
                }
            )
    except Exception:
        # Endpoint remains available even if connector metadata fails.
        pass
    return info


def _coverage_format_schedule_window(code: str, entry: dict) -> str:
    schedule = entry.get("schedule")
    if schedule is None:
        return "janela nao definida"

    minute = str(getattr(schedule, "_orig_minute", "*"))
    hour = str(getattr(schedule, "_orig_hour", "*"))

    if code == "ingest-all-incremental" and hour == "*/2" and minute == "0":
        return "a cada 2h (00:00, 02:00, ...)"
    if hour != "*" and minute != "*":
        return f"diario {hour.zfill(2)}:{minute.zfill(2)}"
    if hour == "*/2" and minute == "0":
        return "a cada 2h"
    return f"cron h={hour} m={minute}"


def _build_investigation_summary(signal: RiskSignal) -> dict:
    factors = signal.factors or {}
    typology_code = signal.typology.code if signal.typology else None

    summary = {
        "what_crossed": [],
        "period_start": signal.period_start,
        "period_end": signal.period_end,
        "observed_total_brl": factors.get("total_value_brl"),
        "legal_threshold_brl": factors.get("threshold_brl"),
        "ratio_over_threshold": factors.get("ratio"),
        "legal_reference": _TYPOLOGY_LEGAL_REFERENCES.get(typology_code),
    }

    if typology_code == "T03":
        summary["what_crossed"] = [
            "orgao_comprador",
            "modalidade_dispensa",
            "grupo_catmat",
            "janela_temporal",
        ]
    elif signal.entity_ids and signal.event_ids:
        summary["what_crossed"] = ["entidades", "eventos", "janela_temporal"]
    else:
        summary["what_crossed"] = ["fatores_quantitativos"]

    return summary


def _apply_signal_filters(
    stmt,
    *,
    typology_code: Optional[str] = None,
    severity: Optional[str] = None,
    period_from: Optional[datetime] = None,
    period_to: Optional[datetime] = None,
    corruption_type: Optional[str] = None,
    sphere: Optional[str] = None,
):
    if typology_code:
        stmt = stmt.where(Typology.code == typology_code)
    if severity:
        stmt = stmt.where(RiskSignal.severity == severity)
    if corruption_type or sphere:
        from shared.typologies.factor_metadata import get_typology_codes_for_filter

        matching_codes = get_typology_codes_for_filter(
            corruption_type=corruption_type,
            sphere=sphere,
        )
        if matching_codes is not None:
            stmt = stmt.where(Typology.code.in_(matching_codes))
    if period_from:
        stmt = stmt.where(RiskSignal.period_end >= period_from)
    if period_to:
        stmt = stmt.where(RiskSignal.period_start <= period_to)
    return stmt


async def get_signals_paginated(
    session: AsyncSession,
    offset: int = 0,
    limit: int = 20,
    typology_code: Optional[str] = None,
    severity: Optional[str] = None,
    sort: str = "analysis_date",
    period_from: Optional[datetime] = None,
    period_to: Optional[datetime] = None,
    corruption_type: Optional[str] = None,
    sphere: Optional[str] = None,
) -> tuple[list[RiskSignalOut], int]:
    """Get risk signals with pagination, filters, and sorting.

    sort: "analysis_date" (default, by period_end DESC) or "ingestion_date" (by created_at DESC)
    period_from / period_to: filter by analysis period (period_start / period_end)
    corruption_type / sphere: filter by legal classification (resolved to typology codes)
    """
    stmt = (
        select(RiskSignal)
        .join(Typology)
        .options(selectinload(RiskSignal.typology))
    )
    count_stmt = select(func.count()).select_from(RiskSignal).join(Typology)

    if typology_code:
        stmt = stmt.where(Typology.code == typology_code)
        count_stmt = count_stmt.where(Typology.code == typology_code)
    if severity:
        stmt = stmt.where(RiskSignal.severity == severity)
        count_stmt = count_stmt.where(RiskSignal.severity == severity)

    # Legal classification filters
    if corruption_type or sphere:
        from shared.typologies.factor_metadata import get_typology_codes_for_filter

        matching_codes = get_typology_codes_for_filter(
            corruption_type=corruption_type, sphere=sphere
        )
        if matching_codes is not None:
            stmt = stmt.where(Typology.code.in_(matching_codes))
            count_stmt = count_stmt.where(Typology.code.in_(matching_codes))

    # Date range filters on analysis period
    if period_from:
        stmt = stmt.where(RiskSignal.period_end >= period_from)
        count_stmt = count_stmt.where(RiskSignal.period_end >= period_from)
    if period_to:
        stmt = stmt.where(RiskSignal.period_start <= period_to)
        count_stmt = count_stmt.where(RiskSignal.period_start <= period_to)

    # Sorting
    if sort == "analysis_date":
        stmt = stmt.order_by(
            RiskSignal.period_end.desc().nulls_last(),
            RiskSignal.created_at.desc(),
        )
    else:
        stmt = stmt.order_by(RiskSignal.created_at.desc())

    total = (await session.execute(count_stmt)).scalar_one()
    result = await session.execute(stmt.offset(offset).limit(limit))
    signals = result.scalars().all()

    return [
        RiskSignalOut(
            id=s.id,
            typology_code=s.typology.code,
            typology_name=s.typology.name,
            severity=SignalSeverity(s.severity),
            confidence=s.data_completeness,
            title=s.title,
            summary=s.summary,
            explanation_md=s.explanation_md,
            completeness_score=s.completeness_score or 0.0,
            completeness_status=s.completeness_status or "insufficient",
            evidence_package_id=s.evidence_package_id,
            factors=s.factors,
            evidence_refs=[EvidenceRef(**ref) for ref in s.evidence_refs],
            entity_ids=[uuid.UUID(eid) for eid in s.entity_ids],
            event_ids=[uuid.UUID(eid) for eid in s.event_ids],
            period_start=s.period_start,
            period_end=s.period_end,
            created_at=s.created_at,
        )
        for s in signals
    ], total


async def get_radar_v2_summary(
    session: AsyncSession,
    *,
    typology_code: Optional[str] = None,
    severity: Optional[str] = None,
    period_from: Optional[datetime] = None,
    period_to: Optional[datetime] = None,
    corruption_type: Optional[str] = None,
    sphere: Optional[str] = None,
) -> RadarV2SummaryResponse:
    count_stmt = (
        select(func.count())
        .select_from(RiskSignal)
        .join(Typology)
    )
    count_stmt = _apply_signal_filters(
        count_stmt,
        typology_code=typology_code,
        severity=severity,
        period_from=period_from,
        period_to=period_to,
        corruption_type=corruption_type,
        sphere=sphere,
    )
    total_signals = int((await session.execute(count_stmt)).scalar_one() or 0)

    sev_stmt = (
        select(RiskSignal.severity, func.count().label("cnt"))
        .select_from(RiskSignal)
        .join(Typology)
    )
    sev_stmt = _apply_signal_filters(
        sev_stmt,
        typology_code=typology_code,
        severity=severity,
        period_from=period_from,
        period_to=period_to,
        corruption_type=corruption_type,
        sphere=sphere,
    ).group_by(RiskSignal.severity)
    sev_rows = (await session.execute(sev_stmt)).all()
    severity_counts = RadarV2SeverityCountsOut(
        **{row.severity: int(row.cnt or 0) for row in sev_rows}
    )

    typo_stmt = (
        select(
            Typology.code.label("code"),
            Typology.name.label("name"),
            func.count().label("cnt"),
        )
        .select_from(RiskSignal)
        .join(Typology)
    )
    typo_stmt = _apply_signal_filters(
        typo_stmt,
        typology_code=typology_code,
        severity=severity,
        period_from=period_from,
        period_to=period_to,
        corruption_type=corruption_type,
        sphere=sphere,
    ).group_by(Typology.code, Typology.name)
    typo_rows = (await session.execute(typo_stmt)).all()
    typology_counts = sorted(
        [
            RadarV2TypologyCountOut(
                code=row.code,
                name=row.name,
                count=int(row.cnt or 0),
            )
            for row in typo_rows
        ],
        key=lambda row: (-row.count, row.code),
    )

    case_stmt = (
        select(func.count(func.distinct(Case.id)))
        .select_from(Case)
        .join(CaseItem, CaseItem.case_id == Case.id)
        .join(RiskSignal, RiskSignal.id == CaseItem.signal_id)
        .join(Typology, Typology.id == RiskSignal.typology_id)
    )
    case_stmt = _apply_signal_filters(
        case_stmt,
        typology_code=typology_code,
        severity=severity,
        period_from=period_from,
        period_to=period_to,
        corruption_type=corruption_type,
        sphere=sphere,
    )
    total_cases = int((await session.execute(case_stmt)).scalar_one() or 0)

    active_filters_count = (
        int(bool(typology_code))
        + int(bool(severity))
        + int(bool(period_from or period_to))
        + int(bool(corruption_type))
        + int(bool(sphere))
    )

    return RadarV2SummaryResponse(
        snapshot_at=datetime.now(timezone.utc),
        totals=RadarV2TotalsOut(signals=total_signals, cases=total_cases),
        severity_counts=severity_counts,
        typology_counts=typology_counts,
        active_filters_count=active_filters_count,
    )


async def get_radar_v2_signals(
    session: AsyncSession,
    *,
    offset: int = 0,
    limit: int = 20,
    typology_code: Optional[str] = None,
    severity: Optional[str] = None,
    sort: str = "analysis_date",
    period_from: Optional[datetime] = None,
    period_to: Optional[datetime] = None,
    corruption_type: Optional[str] = None,
    sphere: Optional[str] = None,
) -> tuple[list[RadarV2SignalListItemOut], int]:
    signals, total = await get_signals_paginated(
        session,
        offset=offset,
        limit=limit,
        typology_code=typology_code,
        severity=severity,
        sort=sort,
        period_from=period_from,
        period_to=period_to,
        corruption_type=corruption_type,
        sphere=sphere,
    )
    items = [
        RadarV2SignalListItemOut(
            id=signal.id,
            typology_code=signal.typology_code,
            typology_name=signal.typology_name,
            severity=signal.severity,
            confidence=signal.confidence,
            title=signal.title,
            summary=signal.summary,
            period_start=signal.period_start,
            period_end=signal.period_end,
            created_at=signal.created_at,
            event_count=len(signal.event_ids or []),
            entity_count=len(signal.entity_ids or []),
            has_graph=len(signal.event_ids or []) > 0,
        )
        for signal in signals
    ]
    return items, total


async def get_entity_by_id(
    session: AsyncSession, entity_id: uuid.UUID
) -> Optional[Entity]:
    """Get entity with aliases."""
    stmt = (
        select(Entity)
        .where(Entity.id == entity_id)
        .options(selectinload(Entity.aliases))
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def resolve_entity_ids_with_clusters(
    session: AsyncSession,
    raw_entity_ids: list[uuid.UUID],
) -> set[uuid.UUID]:
    """
    Given entity UUIDs (possibly pre-merge), returns all UUIDs sharing cluster_ids.
    Single batched query — NEVER call in a loop over signals.
    """
    if not raw_entity_ids:
        return set()
    from sqlalchemy import text
    result = await session.execute(
        text("""
        SELECT DISTINCT e.id FROM entity e
        WHERE e.cluster_id IN (
            SELECT cluster_id FROM entity
            WHERE id = ANY(:ids) AND cluster_id IS NOT NULL
        ) OR e.id = ANY(:ids)
        """),
        {"ids": [str(eid) for eid in raw_entity_ids]},
    )
    return {uuid.UUID(str(row[0])) for row in result.fetchall()}


async def get_case_by_id(
    session: AsyncSession, case_id: uuid.UUID
) -> Optional[Case]:
    """Get case with items and signals."""
    stmt = (
        select(Case)
        .where(Case.id == case_id)
        .options(
            selectinload(Case.items).selectinload(CaseItem.signal).selectinload(
                RiskSignal.typology
            )
        )
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_case_entities_with_roles(
    session: AsyncSession, case_id: uuid.UUID
) -> list[dict]:
    """Entities linked to any signal in the case, with masked identifiers and roles."""
    # Step 1: entity_id → signal_ids mapping via signal_entity
    se_stmt = (
        select(SignalEntity.entity_id, SignalEntity.signal_id)
        .where(
            SignalEntity.signal_id.in_(
                select(CaseItem.signal_id).where(CaseItem.case_id == case_id)
            )
        )
    )
    se_rows = (await session.execute(se_stmt)).all()
    if not se_rows:
        return []

    entity_signal_map: dict[uuid.UUID, list[uuid.UUID]] = defaultdict(list)
    entity_ids: set[uuid.UUID] = set()
    for entity_id, signal_id in se_rows:
        entity_signal_map[entity_id].append(signal_id)
        entity_ids.add(entity_id)

    # Step 2: load entity details
    entity_stmt = (
        select(Entity)
        .where(Entity.id.in_(list(entity_ids)))
        .order_by(Entity.name)
    )
    entities = (await session.execute(entity_stmt)).scalars().all()

    # Step 3: distinct roles for these entities across all their events
    role_stmt = (
        select(EventParticipant.entity_id, EventParticipant.role)
        .where(EventParticipant.entity_id.in_(list(entity_ids)))
        .distinct()
    )
    role_rows = (await session.execute(role_stmt)).all()
    entity_roles: dict[uuid.UUID, set[str]] = defaultdict(set)
    for eid, role in role_rows:
        if role:
            entity_roles[eid].add(role)

    result = []
    for entity in entities:
        identifiers = entity.identifiers or {}
        cnpj_raw = identifiers.get("cnpj", "")
        cnpj_masked = None
        if cnpj_raw and len(cnpj_raw) >= 8:
            cnpj_masked = cnpj_raw[:2] + ".***.***/" + cnpj_raw[-6:]
        result.append(
            {
                "id": entity.id,
                "name": entity.name,
                "type": entity.type,
                "cnpj_masked": cnpj_masked,
                "roles": sorted(entity_roles.get(entity.id, set())),
                "signal_ids": [
                    str(sid) for sid in entity_signal_map.get(entity.id, [])
                ],
            }
        )
    return result


async def get_coverage_list(session: AsyncSession) -> list[CoverageItem]:
    """Build coverage list from ConnectorRegistry, enriched with DB data.

    Always returns an entry for every connector:job pair defined in the
    registry — even when no ingestion has ever run (status="pending").
    """
    from shared.connectors import ConnectorRegistry

    # 1. Existing coverage entries from DB
    cov_rows = (
        await session.execute(select(CoverageRegistry))
    ).scalars().all()
    cov_map = {(r.connector, r.job): r for r in cov_rows}

    # 2. Latest RawRun per connector:job (for real-time status overlay)
    run_rows = (
        await session.execute(
            select(RawRun).order_by(RawRun.created_at.desc()).limit(200)
        )
    ).scalars().all()
    run_map: dict[tuple[str, str], RawRun] = {}
    for r in run_rows:
        key = (r.connector, r.job)
        if key not in run_map:
            run_map[key] = r

    # 3. Build complete list from ConnectorRegistry
    now = datetime.now(tz=timezone.utc)
    items: list[CoverageItem] = []

    for name, cls in ConnectorRegistry.items():
        connector = cls()
        for job in connector.list_jobs():
            key = (name, job.name)
            cov = cov_map.get(key)
            run = run_map.get(key)

            last_run_error = False
            if cov:
                status = cov.status
                last_success = cov.last_success_at
                lag = cov.freshness_lag_hours
                total = cov.total_items
                # Live overrides: correct stale registry with latest run status
                if run and run.status == "error":
                    if not cov.last_success_at:
                        status = "error"
                    else:
                        last_run_error = True
                elif run and run.status == "yielded" and (run.items_fetched or 0) > 0:
                    # Yielded run with data = partial success; override stale
                    # registry until the periodic task refreshes it.
                    if not cov.last_success_at:
                        status = "ok"
                        last_success = run.finished_at
                        lag_delta = (now - run.finished_at) if run.finished_at else None
                        lag = lag_delta.total_seconds() / 3600 if lag_delta else None
            elif run:
                # No pre-computed coverage, derive from latest run
                if run.status == "completed":
                    status = "ok"
                    last_success = run.finished_at
                    lag_delta = (now - run.finished_at) if run.finished_at else None
                    lag = lag_delta.total_seconds() / 3600 if lag_delta else None
                elif run.status == "yielded" and (run.items_fetched or 0) > 0:
                    # Yielded runs that fetched data are partial successes —
                    # the job will resume automatically.  Treat as "ok" so
                    # the pipeline badge reflects reality.
                    status = "ok"
                    last_success = run.finished_at
                    lag_delta = (now - run.finished_at) if run.finished_at else None
                    lag = lag_delta.total_seconds() / 3600 if lag_delta else None
                elif run.status == "error":
                    status = "error"
                    last_success = None
                    lag = None
                else:
                    status = "pending"
                    last_success = None
                    lag = None
                # Use items_normalized (persisted data), not items_fetched
                # (transient raw_source). items_fetched = items_normalized
                # only after normalization completes — before that they differ.
                total = run.items_normalized or 0
            else:
                status = "pending"
                last_success = None
                lag = None
                total = 0

            items.append(
                CoverageItem(
                    connector=name,
                    job=job.name,
                    domain=job.domain,
                    description=job.description,
                    enabled_in_mvp=job.enabled,
                    status=status,
                    last_success_at=last_success,
                    freshness_lag_hours=lag,
                    total_items=total,
                    last_run_error=last_run_error,
                )
            )

    return sorted(items, key=lambda x: (x.connector, x.job))


def _event_region(
    event: Event,
    layer: str,
) -> tuple[str, str] | None:
    attrs = event.attrs or {}

    if layer == "municipio":
        code = (
            attrs.get("cod_ibge")
            or attrs.get("municipio_ibge")
            or attrs.get("municipio_codigo")
            or attrs.get("municipio")
        )
        label = attrs.get("municipio") or attrs.get("localidade") or str(code or "")
    else:
        code = attrs.get("uf") or attrs.get("estado") or attrs.get("sg_uf")
        label = str(code or "")

    if not code:
        return None

    code_str = str(code).strip().upper()
    if not code_str:
        return None

    label_str = str(label or code_str).strip()
    return code_str, label_str


async def get_coverage_map(
    session: AsyncSession,
    layer: str = "uf",
    metric: str = "coverage",
    date_ref: datetime | None = None,
) -> CoverageMapResponse:
    now = datetime.now(timezone.utc)
    ref = date_ref or now
    window_start = ref - timedelta(days=730)

    event_rows = (
        await session.execute(
            select(Event).where(
                Event.occurred_at.isnot(None),
                Event.occurred_at >= window_start,
                Event.occurred_at <= ref,
            )
        )
    ).scalars().all()

    signal_rows = (
        await session.execute(
            select(RiskSignal).where(
                RiskSignal.created_at >= window_start,
                RiskSignal.created_at <= ref,
            )
        )
    ).scalars().all()

    events_by_id: dict[str, Event] = {str(e.id): e for e in event_rows}
    aggregate: dict[str, dict] = defaultdict(
        lambda: {
            "code": "",
            "label": "",
            "event_count": 0,
            "signal_count": 0,
            "latest_event_at": None,
            "risk_sum": 0.0,
            "risk_den": 0,
        }
    )

    for event in event_rows:
        region = _event_region(event, layer=layer)
        if region is None:
            continue
        code, label = region
        bucket = aggregate[code]
        bucket["code"] = code
        bucket["label"] = label
        bucket["event_count"] += 1
        if event.occurred_at and (
            bucket["latest_event_at"] is None or event.occurred_at > bucket["latest_event_at"]
        ):
            bucket["latest_event_at"] = event.occurred_at

    for signal in signal_rows:
        event_ids = [str(eid) for eid in signal.event_ids or []]
        linked_regions: set[str] = set()
        for eid in event_ids:
            event = events_by_id.get(eid)
            if event is None:
                continue
            region = _event_region(event, layer=layer)
            if region is None:
                continue
            code, _label = region
            linked_regions.add(code)

        for code in linked_regions:
            bucket = aggregate.get(code)
            if bucket is None:
                continue
            bucket["signal_count"] += 1
            bucket["risk_sum"] += _SEVERITY_TO_SCORE.get(signal.severity, 0.0)
            bucket["risk_den"] += 1

    max_events = max((data["event_count"] for data in aggregate.values()), default=0)
    items: list[CoverageMapItem] = []
    for data in aggregate.values():
        latest_event_at = data["latest_event_at"]
        freshness_hours = None
        if latest_event_at is not None:
            if latest_event_at.tzinfo is None:
                latest_event_at = latest_event_at.replace(tzinfo=timezone.utc)
            freshness_hours = max((now - latest_event_at).total_seconds() / 3600, 0.0)

        coverage_score = (
            round(data["event_count"] / max_events, 4)
            if max_events > 0
            else 0.0
        )
        risk_score = (
            round(data["risk_sum"] / data["risk_den"], 4)
            if data["risk_den"] > 0
            else 0.0
        )

        if data["event_count"] == 0:
            status = "pending"
        elif freshness_hours is None:
            status = "warning"
        elif freshness_hours < 24:
            status = "ok"
        elif freshness_hours < 72:
            status = "warning"
        else:
            status = "stale"

        items.append(
            CoverageMapItem(
                code=data["code"],
                label=data["label"],
                layer=layer,
                event_count=data["event_count"],
                signal_count=data["signal_count"],
                coverage_score=coverage_score,
                freshness_hours=freshness_hours,
                risk_score=risk_score,
                status=status,
            )
        )

    if metric == "freshness":
        items.sort(key=lambda i: (i.freshness_hours is None, i.freshness_hours or 10**9))
    elif metric == "risk":
        items.sort(key=lambda i: i.risk_score, reverse=True)
    else:
        items.sort(key=lambda i: i.coverage_score, reverse=True)

    return CoverageMapResponse(
        layer=layer,
        metric=metric,
        date_ref=ref,
        generated_at=now,
        items=items,
    )


async def _coverage_get_latest_runs(
    session: AsyncSession,
    *,
    connector: Optional[str] = None,
    limit: int = 1000,
) -> tuple[list[RawRun], dict[tuple[str, str], RawRun]]:
    stmt = select(RawRun).order_by(RawRun.created_at.desc()).limit(limit)
    if connector:
        stmt = stmt.where(RawRun.connector == connector)
    run_rows = (await session.execute(stmt)).scalars().all()

    latest_by_job: dict[tuple[str, str], RawRun] = {}
    for run in run_rows:
        key = (run.connector, run.job)
        if key not in latest_by_job:
            latest_by_job[key] = run
    return run_rows, latest_by_job


async def get_coverage_v2_sources(
    session: AsyncSession,
    *,
    offset: int = 0,
    limit: int = 20,
    status: Optional[str] = None,
    domain: Optional[str] = None,
    enabled_only: bool = False,
    q: Optional[str] = None,
    sort: str = "status_desc",
) -> dict:
    coverage_items = await get_coverage_list(session)
    now = _coverage_now_utc()
    _run_rows, latest_by_job = await _coverage_get_latest_runs(session, limit=600)

    grouped: dict[str, list[CoverageItem]] = defaultdict(list)
    for item in coverage_items:
        grouped[item.connector].append(item)

    q_normalized = (q or "").strip().lower()
    rows: list[CoverageV2SourceItem] = []

    for connector, connector_items in grouped.items():
        selected_jobs: list[CoverageItem] = []
        for item in connector_items:
            if enabled_only and not bool(item.enabled_in_mvp):
                continue
            if domain and item.domain != domain:
                continue
            if q_normalized:
                haystack = " ".join(
                    [
                        connector.lower(),
                        item.job.lower(),
                        (item.domain or "").lower(),
                        (item.description or "").lower(),
                    ]
                )
                if q_normalized not in haystack:
                    continue
            selected_jobs.append(item)

        if not selected_jobs:
            continue

        status_counts = _coverage_empty_status_counts()
        for item in selected_jobs:
            status_counts[str(item.status)] += 1

        worst_status = _coverage_worst_status(status_counts)
        if status and worst_status != status:
            continue

        running_jobs = 0
        stuck_jobs = 0
        error_jobs = 0
        active_job_names: list[str] = []
        items_fetched_live = 0
        items_normalized_live = 0
        earliest_running_start: datetime | None = None
        for item in selected_jobs:
            run = latest_by_job.get((item.connector, item.job))
            if run is None:
                continue
            if run.status == "running":
                running_jobs += 1
                active_job_names.append(item.job)
                items_fetched_live += run.items_fetched or 0
                items_normalized_live += run.items_normalized or 0
                if run.created_at:
                    if earliest_running_start is None or run.created_at < earliest_running_start:
                        earliest_running_start = run.created_at
                if _coverage_is_stuck_run(run, now):
                    stuck_jobs += 1
            elif run.status == "error":
                error_jobs += 1

        elapsed_seconds = None
        estimated_rate = None
        if earliest_running_start is not None:
            elapsed_seconds = (now - earliest_running_start).total_seconds()
            if elapsed_seconds > 0 and items_fetched_live > 0:
                estimated_rate = round((items_fetched_live / elapsed_seconds) * 60, 1)

        last_success_values = [item.last_success_at for item in selected_jobs if item.last_success_at]
        lag_values = [item.freshness_lag_hours for item in selected_jobs if item.freshness_lag_hours is not None]

        rows.append(
            CoverageV2SourceItem(
                connector=connector,
                connector_label=_coverage_connector_label(connector),
                job_count=len(selected_jobs),
                enabled_job_count=sum(1 for item in selected_jobs if item.enabled_in_mvp),
                worst_status=worst_status,  # type: ignore[arg-type]
                status_counts=CoverageV2StatusCounts(**status_counts),
                runtime=CoverageV2SourceRuntime(
                    running_jobs=running_jobs,
                    stuck_jobs=stuck_jobs,
                    error_jobs=error_jobs,
                    active_job_names=active_job_names,
                    items_fetched_live=items_fetched_live,
                    items_normalized_live=items_normalized_live,
                    elapsed_seconds=round(elapsed_seconds, 1) if elapsed_seconds is not None else None,
                    estimated_rate_per_min=estimated_rate,
                ),
                last_success_at=max(last_success_values) if last_success_values else None,
                max_freshness_lag_hours=max(lag_values) if lag_values else None,
            )
        )

    if sort == "name_asc":
        rows.sort(key=lambda row: row.connector_label.lower())
    elif sort == "freshness_desc":
        rows.sort(
            key=lambda row: (
                row.max_freshness_lag_hours is None,
                -(row.max_freshness_lag_hours or 0.0),
                row.connector_label.lower(),
            )
        )
    elif sort == "jobs_desc":
        rows.sort(key=lambda row: (-row.job_count, row.connector_label.lower()))
    else:
        rows.sort(
            key=lambda row: (
                -_COVERAGE_STATUS_RANK.get(row.worst_status, 0),
                row.connector_label.lower(),
            )
        )

    total = len(rows)
    paginated = rows[offset : offset + limit]
    return CoverageV2SourcesResponse(
        items=paginated,
        total=total,
        offset=offset,
        limit=limit,
    ).model_dump()


async def get_coverage_v2_summary(session: AsyncSession) -> dict:
    from shared.scheduler.schedule import BEAT_SCHEDULE

    now = _coverage_now_utc()
    coverage_items = await get_coverage_list(session)
    _run_rows, latest_by_job = await _coverage_get_latest_runs(session, limit=600)

    status_counts = _coverage_empty_status_counts()
    for item in coverage_items:
        status_counts[str(item.status)] += 1

    runtime_running = 0
    runtime_stuck = 0
    runtime_error = 0
    # Only count errors from the last 2 hours as actively blocking.
    # Older errors (e.g. from docker restarts) are stale and will be
    # resolved by the next scheduled ingest — they shouldn't block the
    # pipeline dashboard permanently.
    _recent_error_cutoff = now - timedelta(hours=2)
    for run in latest_by_job.values():
        if run.status == "running":
            runtime_running += 1
            if _coverage_is_stuck_run(run, now):
                runtime_stuck += 1
        elif run.status == "error" and run.created_at and run.created_at >= _recent_error_cutoff:
            runtime_error += 1

    # Use pg_class.reltuples for instant approximate counts instead of
    # sequential COUNT(*) scans on multi-million-row tables.
    _estimate_sql = text(
        "SELECT relname, GREATEST(reltuples, 0)::bigint AS est "
        "FROM pg_class "
        "WHERE relname IN ('event', 'graph_node', 'graph_edge', 'baseline_snapshot', 'risk_signal')"
    )
    _est_rows = (await session.execute(_estimate_sql)).all()
    _est = {r.relname: int(r.est) for r in _est_rows}
    event_count = _est.get("event", 0)
    graph_nodes = _est.get("graph_node", 0)
    graph_edges = _est.get("graph_edge", 0)
    baseline_count = _est.get("baseline_snapshot", 0)
    signal_count = _est.get("risk_signal", 0)
    er_state = _coverage_scalar_one_or_none(
        await session.execute(select(ERRunState).order_by(ERRunState.created_at.desc()).limit(1))
    )

    # ── Ingest stage (no upstream dependency) ──────────────────────────
    if not coverage_items or status_counts["pending"] == len(coverage_items):
        ingest_stage = CoverageV2PipelineStage(
            code="ingest",
            label="Ingestao de Dados",
            status="pending",
            reason="Nenhuma fonte de dados ingerida ainda.",
        )
    elif runtime_running > 0:
        ingest_stage = CoverageV2PipelineStage(
            code="ingest",
            label="Ingestao de Dados",
            status="processing",
            reason=f"{runtime_running} job(s) em execucao no momento.",
        )
    elif status_counts["error"] > 0:
        ingest_stage = CoverageV2PipelineStage(
            code="ingest",
            label="Ingestao de Dados",
            status="error",
            reason="Existem jobs com erro recente.",
        )
    elif status_counts["warning"] > 0 or status_counts["stale"] > 0:
        ingest_stage = CoverageV2PipelineStage(
            code="ingest",
            label="Ingestao de Dados",
            status="warning",
            reason="Ha fontes com dados desatualizados ou em atencao.",
        )
    else:
        ingest_stage = CoverageV2PipelineStage(
            code="ingest",
            label="Ingestao de Dados",
            status="up_to_date",
            reason="Fontes principais com atualizacao recente.",
        )

    # ── ER stage (depends on ingest) ─────────────────────────────────
    if event_count == 0:
        er_stage = CoverageV2PipelineStage(
            code="entity_resolution",
            label="Resolucao de Entidades",
            status="pending",
            reason="Aguardando dados para iniciar vinculacao.",
        )
    elif er_state is not None and er_state.status == "running":
        er_stage = CoverageV2PipelineStage(
            code="entity_resolution",
            label="Resolucao de Entidades",
            status="processing",
            reason="Resolucao de entidades em processamento.",
        )
    elif er_state is not None and er_state.status == "error":
        er_stage = CoverageV2PipelineStage(
            code="entity_resolution",
            label="Resolucao de Entidades",
            status="error",
            reason="Ultima execucao de resolucao falhou.",
        )
    elif er_state is None or er_state.status != "completed":
        er_stage = CoverageV2PipelineStage(
            code="entity_resolution",
            label="Resolucao de Entidades",
            status="pending",
            reason="Aguardando primeira execucao completa.",
        )
    elif ingest_stage.status in {"processing", "error", "warning"}:
        er_stage = CoverageV2PipelineStage(
            code="entity_resolution",
            label="Resolucao de Entidades",
            status="stale",
            reason="Novos dados em ingestao; re-execucao pendente apos conclusao.",
        )
    elif graph_nodes == 0:
        er_stage = CoverageV2PipelineStage(
            code="entity_resolution",
            label="Resolucao de Entidades",
            status="warning",
            reason="Ainda sem nos materializados no grafo.",
        )
    elif graph_edges == 0:
        er_stage = CoverageV2PipelineStage(
            code="entity_resolution",
            label="Resolucao de Entidades",
            status="warning",
            reason="Nos criados, mas sem ligacoes entre entidades.",
        )
    else:
        er_stage = CoverageV2PipelineStage(
            code="entity_resolution",
            label="Resolucao de Entidades",
            status="up_to_date",
            reason=f"Entidades e ligacoes materializadas ({graph_nodes} nos, {graph_edges} arestas).",
        )

    # ── Baselines stage (depends on ingest + ER) ─────────────────────
    if baseline_count == 0:
        if ingest_stage.status == "pending":
            bl_reason = "Aguardando ingestao de dados."
        elif er_stage.status in {"pending", "processing"}:
            bl_reason = "Aguardando resolucao de entidades."
        else:
            bl_reason = "Nenhum baseline calculado ainda."
        baseline_stage = CoverageV2PipelineStage(
            code="baselines",
            label="Calculo de Baselines",
            status="pending",
            reason=bl_reason,
        )
    elif ingest_stage.status == "processing" or er_stage.status in {"processing", "stale"}:
        baseline_stage = CoverageV2PipelineStage(
            code="baselines",
            label="Calculo de Baselines",
            status="stale",
            reason="Baselines existem, mas novos dados requerem recalculo.",
        )
    else:
        baseline_stage = CoverageV2PipelineStage(
            code="baselines",
            label="Calculo de Baselines",
            status="up_to_date",
            reason=f"{baseline_count} baseline(s) atualizados.",
        )

    # ── Signals stage (depends on ingest + ER + baselines) ───────────
    if signal_count == 0:
        if baseline_count == 0:
            sig_reason = "Aguardando calculo de baselines."
        elif er_stage.status in {"pending", "processing"}:
            sig_reason = "Aguardando resolucao de entidades."
        else:
            sig_reason = "Nenhum sinal detectado ainda."
        signal_stage = CoverageV2PipelineStage(
            code="signals",
            label="Deteccao de Sinais",
            status="pending",
            reason=sig_reason,
        )
    elif (
        ingest_stage.status == "processing"
        or er_stage.status in {"stale", "processing"}
        or baseline_stage.status in {"stale", "processing"}
    ):
        signal_stage = CoverageV2PipelineStage(
            code="signals",
            label="Deteccao de Sinais",
            status="stale",
            reason=f"{signal_count} sinais detectados, mas pipeline upstream em execucao — re-deteccao pendente.",
        )
    else:
        signal_stage = CoverageV2PipelineStage(
            code="signals",
            label="Deteccao de Sinais",
            status="up_to_date",
            reason=f"{signal_count} sinais de risco detectados.",
        )

    # ── Overall status ───────────────────────────────────────────────
    # "blocked" = stuck workers (truly hung, need intervention)
    # "error"   = pipeline stage errors or recent job failures (auto-retry pending)
    # "attention" = processing/stale/pending stages (normal pipeline progression)
    stages = [ingest_stage, er_stage, baseline_stage, signal_stage]
    if runtime_stuck > 0 or any(s.status == "error" for s in stages):
        overall_status = "blocked"
    elif runtime_error > 0:
        overall_status = "attention"
    elif any(s.status in {"stale", "processing", "pending", "warning"} for s in stages):
        overall_status = "attention"
    else:
        overall_status = "healthy"

    schedule_windows = [
        CoverageV2ScheduleWindow(
            job_code=code,
            window=_coverage_format_schedule_window(code, entry),
        )
        for code, entry in BEAT_SCHEDULE.items()
    ]

    return CoverageV2SummaryResponse(
        snapshot_at=now,
        totals=CoverageV2Totals(
            connectors=len({item.connector for item in coverage_items}),
            jobs=len(coverage_items),
            jobs_enabled=sum(1 for item in coverage_items if item.enabled_in_mvp),
            signals_total=signal_count,
            status_counts=CoverageV2StatusCounts(**status_counts),
            runtime=CoverageV2RuntimeTotals(
                running=runtime_running,
                stuck=runtime_stuck,
                failed_or_stuck=runtime_error + runtime_stuck,
            ),
        ),
        pipeline=CoverageV2PipelineSummary(
            overall_status=overall_status,  # type: ignore[arg-type]
            stages=stages,
        ),
        schedule_windows_brt=schedule_windows,
    ).model_dump()


async def get_coverage_v2_source_preview(
    session: AsyncSession,
    connector: str,
    *,
    runs_limit: int = 10,
) -> Optional[dict]:
    coverage_items = await get_coverage_list(session)
    connector_jobs = [item for item in coverage_items if item.connector == connector]
    if not connector_jobs:
        return None

    now = _coverage_now_utc()
    run_rows, latest_by_job = await _coverage_get_latest_runs(
        session,
        connector=connector,
        limit=max(120, runs_limit * 12),
    )

    status_counts = _coverage_empty_status_counts()
    job_items: list[CoverageV2SourcePreviewJob] = []
    for item in sorted(
        connector_jobs,
        key=lambda row: (
            -_COVERAGE_STATUS_RANK.get(row.status, 0),
            row.job,
        ),
    ):
        status_counts[item.status] += 1
        latest_run = latest_by_job.get((connector, item.job))
        job_items.append(
            CoverageV2SourcePreviewJob(
                job=item.job,
                domain=item.domain,
                description=item.description,
                enabled_in_mvp=bool(item.enabled_in_mvp),
                status=item.status,  # type: ignore[arg-type]
                total_items=item.total_items,
                last_success_at=item.last_success_at,
                freshness_lag_hours=item.freshness_lag_hours,
                latest_run=(
                    _coverage_latest_run_to_model(latest_run, now)
                    if latest_run is not None
                    else None
                ),
            )
        )

    recent_runs: list[CoverageV2LatestRun] = [
        _coverage_latest_run_to_model(run, now)
        for run in run_rows[:runs_limit]
    ]

    worst_status = _coverage_worst_status(status_counts)
    insights: list[str] = []
    stuck_count = sum(1 for run in recent_runs if run.is_stuck)
    error_count = sum(1 for run in recent_runs if run.status == "error")
    if stuck_count > 0:
        insights.append(f"{stuck_count} execucao(oes) em andamento acima de 20 minutos.")
    if error_count > 0:
        insights.append(f"{error_count} execucao(oes) recente(s) com erro.")
    if status_counts["pending"] == len(connector_jobs):
        insights.append("Fonte aguardando primeira ingestao de dados.")
    if not insights:
        insights.append("Fonte operando dentro do comportamento esperado no periodo recente.")

    return CoverageV2SourcePreviewResponse(
        connector=CoverageV2SourcePreviewConnector(
            connector=connector,
            connector_label=_coverage_connector_label(connector),
            worst_status=worst_status,  # type: ignore[arg-type]
            job_count=len(connector_jobs),
            enabled_job_count=sum(1 for item in connector_jobs if item.enabled_in_mvp),
            status_counts=CoverageV2StatusCounts(**status_counts),
        ),
        jobs=job_items,
        recent_runs=recent_runs,
        insights=insights,
    ).model_dump()


async def get_coverage_v2_map(
    session: AsyncSession,
    *,
    layer: str = "uf",
    metric: str = "coverage",
) -> dict:
    base_map = await get_coverage_map(session, layer=layer, metric=metric)
    regions_with_data = sum(1 for item in base_map.items if item.event_count > 0)
    regions_without_data = len(base_map.items) - regions_with_data
    total_events = sum(int(item.event_count) for item in base_map.items)
    total_signals = sum(int(item.signal_count) for item in base_map.items)

    return CoverageV2MapResponse(
        layer=base_map.layer,
        metric=base_map.metric,
        generated_at=base_map.generated_at,
        date_ref=base_map.date_ref,
        national=CoverageV2MapNational(
            regions_with_data=regions_with_data,
            regions_without_data=regions_without_data,
            total_events=total_events,
            total_signals=total_signals,
        ),
        items=base_map.items,
    ).model_dump()


async def get_coverage_v2_analytics(session: AsyncSession) -> dict:
    items = await get_analytical_coverage(session)
    apt_count = sum(1 for item in items if bool(item.get("apt")))
    blocked_count = sum(1 for item in items if not bool(item.get("apt")))
    with_signals_30d = sum(1 for item in items if int(item.get("signals_30d") or 0) > 0)
    return CoverageV2AnalyticsResponse(
        summary=CoverageV2AnalyticsSummary(
            total_typologies=len(items),
            apt_count=apt_count,
            blocked_count=blocked_count,
            with_signals_30d=with_signals_30d,
        ),
        items=items,
    ).model_dump()


async def get_coverage_v2_run_detail(
    session: AsyncSession,
    run_id: uuid.UUID,
) -> Optional[dict]:
    run = _coverage_scalar_one_or_none(
        await session.execute(select(RawRun).where(RawRun.id == run_id))
    )
    if run is None:
        return None

    now = datetime.now(timezone.utc)

    summary_row = _coverage_row_one_or_none(
        await session.execute(
            select(
                func.count(RawSource.id).label("records_stored"),
                func.count(func.distinct(RawSource.raw_id)).label("distinct_raw_ids"),
                func.min(RawSource.created_at).label("first_record_at"),
                func.max(RawSource.created_at).label("last_record_at"),
            ).where(RawSource.run_id == run_id)
        )
    )
    # raw_source rows are deleted after normalization, so count from raw_source is always 0.
    # Use items_normalized from the run record as the canonical "records persisted" count.
    records_stored = int(run.items_normalized or 0)
    distinct_raw_ids = int(getattr(summary_row, "distinct_raw_ids", 0) or 0)
    # Duplicate detection is only possible while raw_source exists (pre-normalization).
    # After deletion distinct_raw_ids==0, so avoid falsely reporting everything as duplicate.
    duplicate_raw_ids = max(records_stored - distinct_raw_ids, 0) if distinct_raw_ids > 0 else 0

    profile_sources = (
        await session.execute(
            select(RawSource.raw_data)
            .where(RawSource.run_id == run_id)
            .order_by(RawSource.created_at.desc())
            .limit(_COVERAGE_PROFILE_SAMPLE_LIMIT)
        )
    ).scalars().all()

    field_stats: dict[str, dict[str, Any]] = {}
    profile_total = 0
    for raw_data in profile_sources:
        if not isinstance(raw_data, dict):
            continue
        profile_total += 1
        for key, value in raw_data.items():
            stat = field_stats.setdefault(
                key,
                {"count": 0, "types": set(), "examples": [], "fingerprints": set()},
            )
            stat["count"] += 1
            stat["types"].add(_coverage_value_type(value))
            if len(stat["examples"]) < 3:
                preview = _coverage_preview_value(value)
                fingerprint = _coverage_example_fingerprint(preview)
                if fingerprint not in stat["fingerprints"]:
                    stat["examples"].append(preview)
                    stat["fingerprints"].add(fingerprint)

    field_profile = [
        CoverageV2RunFieldProfile(
            key=key,
            present_count=stats["count"],
            coverage_pct=round((stats["count"] / profile_total * 100.0), 2)
            if profile_total
            else 0.0,
            detected_types=sorted(list(stats["types"])),
            examples=stats["examples"],
        )
        for key, stats in sorted(
            field_stats.items(),
            key=lambda item: (-item[1]["count"], item[0]),
        )
    ]

    sample_rows = (
        await session.execute(
            select(RawSource)
            .where(RawSource.run_id == run_id)
            .order_by(RawSource.created_at.desc())
            .limit(_COVERAGE_RECORD_SAMPLE_LIMIT)
        )
    ).scalars().all()

    samples = [
        CoverageV2RunSampleRecord(
            raw_id=row.raw_id,
            created_at=_coverage_safe_iso(row.created_at),
            preview=_coverage_build_preview(row.raw_data if isinstance(row.raw_data, dict) else {}),
            raw_data=_coverage_trim_raw_data(row.raw_data if isinstance(row.raw_data, dict) else {}),
        )
        for row in sample_rows
    ]

    # Parse progress metadata for live tracking
    cursor_label, _win_idx, _page_num = _parse_cursor_info(run.cursor_end)
    progress_meta: dict[str, Any] = {}
    if run.errors and isinstance(run.errors, dict):
        pm = run.errors.get("_progress")
        if pm and isinstance(pm, dict):
            progress_meta = pm
    elapsed_seconds = None
    if run.status == "running" and run.created_at:
        elapsed_seconds = round((now - run.created_at).total_seconds(), 1)

    return CoverageV2RunDetailResponse(
        run={
            "id": str(run.id),
            "connector": run.connector,
            "job": run.job,
            "status": run.status,
            "cursor_start": run.cursor_start,
            "cursor_end": run.cursor_end,
            "cursor_info": cursor_label,
            "items_fetched": run.items_fetched,
            "items_normalized": run.items_normalized,
            "errors": run.errors,
            "started_at": _coverage_safe_iso(run.created_at),
            "finished_at": _coverage_safe_iso(run.finished_at),
            "elapsed_seconds": elapsed_seconds,
            "rate_per_min": progress_meta.get("rate_per_min"),
            "pages_fetched": progress_meta.get("pages"),
        },
        job=_coverage_build_job_info(run.connector, run.job),
        summary={
            "records_stored": records_stored,
            "distinct_raw_ids": distinct_raw_ids,
            "duplicate_raw_ids": duplicate_raw_ids,
            "first_record_at": _coverage_safe_iso(getattr(summary_row, "first_record_at", None)),
            "last_record_at": _coverage_safe_iso(getattr(summary_row, "last_record_at", None)),
            "profile_sampled_records": profile_total,
            "profile_sample_limit": _COVERAGE_PROFILE_SAMPLE_LIMIT,
        },
        field_profile=field_profile,
        samples=samples,
    ).model_dump()


def build_signal_replay_hash(signal: RiskSignal, evidence_package: EvidencePackage | None) -> str:
    payload = {
        "signal": {
            "id": str(signal.id),
            "typology_id": str(signal.typology_id),
            "severity": signal.severity,
            "confidence": signal.data_completeness,
            "title": signal.title,
            "summary": signal.summary,
            "completeness_score": signal.completeness_score,
            "completeness_status": signal.completeness_status,
            "factors": signal.factors or {},
            "evidence_refs": signal.evidence_refs or [],
            "entity_ids": signal.entity_ids or [],
            "event_ids": signal.event_ids or [],
            "period_start": signal.period_start.isoformat() if signal.period_start else None,
            "period_end": signal.period_end.isoformat() if signal.period_end else None,
        },
        "evidence_package": {
            "id": str(evidence_package.id) if evidence_package else None,
            "source_url": evidence_package.source_url if evidence_package else None,
            "source_hash": evidence_package.source_hash if evidence_package else None,
            "captured_at": (
                evidence_package.captured_at.isoformat()
                if evidence_package and evidence_package.captured_at
                else None
            ),
            "parser_version": evidence_package.parser_version if evidence_package else None,
            "model_version": evidence_package.model_version if evidence_package else None,
            "raw_snapshot_uri": evidence_package.raw_snapshot_uri if evidence_package else None,
            "normalized_snapshot_uri": (
                evidence_package.normalized_snapshot_uri if evidence_package else None
            ),
        },
    }
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


async def get_signal_by_id(
    session: AsyncSession,
    signal_id: uuid.UUID,
) -> Optional[RiskSignal]:
    stmt = (
        select(RiskSignal)
        .where(RiskSignal.id == signal_id)
        .options(selectinload(RiskSignal.typology))
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_signal_detail(
    session: AsyncSession,
    signal_id: uuid.UUID,
) -> Optional[dict]:
    """Get signal detail with associated case, resolved entities, and factor metadata."""
    signal = await get_signal_by_id(session, signal_id)
    if signal is None:
        return None

    # Find associated case through CaseItem join
    case_stmt = (
        select(Case)
        .join(CaseItem)
        .where(CaseItem.signal_id == signal_id)
    )
    case = (await session.execute(case_stmt)).scalar_one_or_none()

    # Resolve entity_ids into full entity data with roles
    entities_out: list[dict] = []
    raw_entity_ids = signal.entity_ids or []
    parsed_event_ids = _to_uuid_list(signal.event_ids or [])
    if raw_entity_ids:
        parsed_eids = _to_uuid_list(raw_entity_ids)
        entity_stmt = select(Entity).where(Entity.id.in_(parsed_eids))
        entity_result = await session.execute(entity_stmt)
        entity_map = {e.id: e for e in entity_result.scalars().all()}

        # Get roles from event_participant constrained to this signal's events.
        role_rows = []
        if parsed_event_ids:
            role_stmt = (
                select(
                    EventParticipant.entity_id,
                    EventParticipant.role,
                    func.count().label("cnt"),
                )
                .where(
                    EventParticipant.entity_id.in_(parsed_eids),
                    EventParticipant.event_id.in_(parsed_event_ids),
                )
                .group_by(EventParticipant.entity_id, EventParticipant.role)
            )
            role_result = await session.execute(role_stmt)
            role_rows = role_result.all()

        # Build roles map: entity_id -> [(role, count)]
        roles_map: dict[uuid.UUID, list[tuple[str, int]]] = defaultdict(list)
        for row in role_rows:
            roles_map[row.entity_id].append((row.role, row.cnt))

        for eid in parsed_eids:
            entity = entity_map.get(eid)
            if entity is None:
                entities_out.append({
                    "id": str(eid),
                    "type": "unknown",
                    "name": str(eid)[:8] + "...",
                    "identifiers": {},
                    "roles": [],
                    "roles_detailed": [],
                    "role_explanation": None,
                })
                continue

            role_pairs = roles_map.get(eid, [])
            roles = sorted({r for r, _ in role_pairs})
            roles_detailed = [
                {
                    "code": role,
                    "label": _role_label(role),
                    "count_in_signal": int(cnt),
                }
                for role, cnt in sorted(role_pairs, key=lambda x: (-x[1], x[0]))
            ]
            role_explanation = None
            if role_pairs:
                parts = [
                    f"{_role_label(r)} ({r}) em {c} evento(s)"
                    for r, c in sorted(role_pairs, key=lambda x: (-x[1], x[0]))
                ]
                role_explanation = ", ".join(parts)

            entities_out.append({
                "id": str(entity.id),
                "type": entity.type,
                "name": entity.name,
                "identifiers": entity.identifiers or {},
                "roles": roles,
                "roles_detailed": roles_detailed,
                "role_explanation": role_explanation,
            })

    # Factor descriptions (lazy import to avoid circular dependency)
    from shared.typologies.factor_metadata import get_factor_descriptions
    factor_descriptions = get_factor_descriptions(
        signal.factors or {},
        typology_code=signal.typology.code if signal.typology else None,
    )

    evidence_total = len(signal.event_ids or [])
    evidence_listed = len(signal.evidence_refs or [])

    return {
        "id": signal.id,
        "typology_code": signal.typology.code,
        "typology_name": signal.typology.name,
        "severity": signal.severity,
        "confidence": signal.data_completeness,
        "title": signal.title,
        "summary": signal.summary,
        "explanation_md": signal.explanation_md,
        "completeness_score": signal.completeness_score,
        "completeness_status": signal.completeness_status,
        "factors": signal.factors,
        "factor_descriptions": factor_descriptions,
        "evidence_refs": signal.evidence_refs,
        "evidence_stats": {
            "total_events": evidence_total,
            "listed_refs": evidence_listed,
            "omitted_refs": max(0, evidence_total - evidence_listed),
        },
        "investigation_summary": _build_investigation_summary(signal),
        "entity_ids": signal.entity_ids,
        "entities": entities_out,
        "event_ids": signal.event_ids,
        "period_start": signal.period_start,
        "period_end": signal.period_end,
        "evidence_package_id": str(signal.evidence_package_id) if signal.evidence_package_id else None,
        "created_at": signal.created_at,
        "case_id": str(case.id) if case else None,
        "case_title": case.title if case else None,
    }


async def get_signal_graph(
    session: AsyncSession,
    signal_id: uuid.UUID,
    mode: str = "overview",
) -> Optional[SignalGraphResponse]:
    signal = await get_signal_by_id(session, signal_id)
    if signal is None:
        return None

    parsed_event_ids = _to_uuid_list(signal.event_ids or [])
    signal_out = SignalGraphSignalOut(
        id=signal.id,
        typology_code=signal.typology.code,
        typology_name=signal.typology.name,
        severity=signal.severity,
        confidence=signal.data_completeness,
        title=signal.title,
        period_start=signal.period_start,
        period_end=signal.period_end,
    )

    factors = signal.factors or {}
    if signal.typology.code == "T03":
        n_purchases = factors.get("n_purchases") or factors.get("cluster_count")
        total_value = factors.get("total_value_brl") or factors.get("cluster_value")
        threshold = factors.get("threshold_brl")
        ratio = factors.get("ratio") or factors.get("threshold_ratio")
        if isinstance(n_purchases, (int, float)) and isinstance(total_value, (int, float)):
            why_flagged = (
                f"Foram agrupados {int(n_purchases)} eventos na mesma janela temporal, "
                f"totalizando R$ {float(total_value):,.2f}."
            )
            if isinstance(ratio, (int, float)) and isinstance(threshold, (int, float)):
                why_flagged += (
                    f" O total ficou {float(ratio):.2f}x acima do limite de "
                    f"R$ {float(threshold):,.2f}."
                )
        else:
            why_flagged = signal.summary or "Padrao atipico identificado na analise automatica."
    else:
        why_flagged = signal.summary or "Padrao atipico identificado na analise automatica."

    if not parsed_event_ids:
        return SignalGraphResponse(
            signal=signal_out,
            pattern_story=SignalPatternStoryOut(
                pattern_label=signal.typology.name,
                started_at=signal.period_start,
                ended_at=signal.period_end,
                started_from_entities=[],
                flow_targets=[],
                why_flagged=why_flagged,
            ),
            overview=SignalGraphOverviewOut(nodes=[], edges=[]),
            timeline=[],
            involved_entities=[],
            diagnostics=SignalGraphDiagnosticsOut(
                events_total=0,
                events_loaded=0,
                events_missing=0,
                participants_total=0,
                unique_entities=0,
                has_minimum_network=False,
                fallback_reason="no_event_ids",
            ),
        )

    event_stmt = select(Event).where(Event.id.in_(parsed_event_ids))
    events = list((await session.execute(event_stmt)).scalars().all())
    event_by_id = {event.id: event for event in events}

    participant_stmt = (
        select(EventParticipant, Entity)
        .join(Entity, Entity.id == EventParticipant.entity_id)
        .where(EventParticipant.event_id.in_(parsed_event_ids))
    )
    participant_rows = list(await session.execute(participant_stmt))

    participants_by_event: dict[uuid.UUID, list[SignalTimelineParticipantOut]] = defaultdict(list)
    entity_profiles: dict[uuid.UUID, Entity] = {}
    role_counts: dict[uuid.UUID, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    entity_event_sets: dict[uuid.UUID, set[uuid.UUID]] = defaultdict(set)

    for row in participant_rows:
        participant = row[0]
        entity = row[1]
        if participant is None or entity is None:
            continue
        role = (participant.role or "unknown").strip()
        entity_profiles[entity.id] = entity
        role_counts[entity.id][role] += 1
        entity_event_sets[entity.id].add(participant.event_id)
        participants_by_event[participant.event_id].append(
            SignalTimelineParticipantOut(
                entity_id=entity.id,
                name=entity.name,
                node_type=entity.type,
                role=role,
                role_label=_role_label(role),
            )
        )

    ordered_events = sorted(
        [event for event in events if event.id in set(parsed_event_ids)],
        key=_event_sort_key,
    )

    timeline: list[SignalTimelineEventOut] = []
    for event in ordered_events:
        event_participants = sorted(
            participants_by_event.get(event.id, []),
            key=lambda p: (p.role, p.name.lower()),
        )
        timeline.append(
            SignalTimelineEventOut(
                event_id=event.id,
                occurred_at=event.occurred_at,
                value_brl=event.value_brl,
                description=event.description or f"Evento {event.id}",
                source_connector=event.source_connector,
                source_id=event.source_id,
                participants=event_participants,
                evidence_reason="Compoe o fluxo cronologico e o cruzamento de participantes do sinal",
                attrs=event.attrs or {},
            )
        )

    edge_acc: dict[
        tuple[uuid.UUID, uuid.UUID, str, str],
        dict,
    ] = {}

    for event in timeline:
        event_participants = event.participants
        if len(event_participants) < 2:
            continue

        initiators = [p for p in event_participants if p.role.lower() in _INITIATOR_ROLES]
        targets = [p for p in event_participants if p.role.lower() in _TARGET_ROLES]

        directed_pairs: list[tuple[SignalTimelineParticipantOut, SignalTimelineParticipantOut]] = []
        if initiators and targets:
            for source in initiators:
                for target in targets:
                    if source.entity_id != target.entity_id:
                        directed_pairs.append((source, target))
        else:
            for i in range(len(event_participants)):
                for j in range(i + 1, len(event_participants)):
                    left = event_participants[i]
                    right = event_participants[j]
                    if left.role.lower() in _INITIATOR_ROLES and right.role.lower() in _TARGET_ROLES:
                        directed_pairs.append((left, right))
                        continue
                    if right.role.lower() in _INITIATOR_ROLES and left.role.lower() in _TARGET_ROLES:
                        directed_pairs.append((right, left))
                        continue
                    if str(left.entity_id) <= str(right.entity_id):
                        directed_pairs.append((left, right))
                    else:
                        directed_pairs.append((right, left))

        for source, target in directed_pairs:
            key = (source.entity_id, target.entity_id, source.role, target.role)
            entry = edge_acc.setdefault(
                key,
                {
                    "event_ids": set(),
                    "first_seen_at": None,
                    "last_seen_at": None,
                    "weight": 0.0,
                },
            )
            entry["event_ids"].add(event.event_id)
            entry["weight"] += 1.0
            if event.occurred_at is not None:
                if entry["first_seen_at"] is None or event.occurred_at < entry["first_seen_at"]:
                    entry["first_seen_at"] = event.occurred_at
                if entry["last_seen_at"] is None or event.occurred_at > entry["last_seen_at"]:
                    entry["last_seen_at"] = event.occurred_at

    involved_entities = sorted(
        entity_profiles.values(),
        key=lambda entity: (-len(entity_event_sets.get(entity.id, set())), entity.name.lower()),
    )

    nodes = [
        SignalGraphNodeOut(
            id=entity.id,
            entity_id=entity.id,
            label=entity.name,
            node_type=entity.type,
            attrs={
                "identifiers": entity.identifiers or {},
                "attrs": entity.attrs or {},
                "photo_url": _extract_photo_url(entity.attrs or {}),
            },
        )
        for entity in involved_entities
    ]

    edges: list[SignalGraphEdgeOut] = []
    for (from_entity_id, to_entity_id, source_role, target_role), data in sorted(
        edge_acc.items(),
        key=lambda item: (
            -(len(item[1]["event_ids"])),
            str(item[0][0]),
            str(item[0][1]),
        ),
    ):
        edge_id = str(
            uuid.uuid5(
                uuid.NAMESPACE_URL,
                f"{signal.id}:{from_entity_id}:{to_entity_id}:{source_role}:{target_role}",
            )
        )
        event_ids_sorted = sorted(
            data["event_ids"],
            key=lambda event_id: (
                event_by_id.get(event_id).occurred_at
                if event_by_id.get(event_id) and event_by_id.get(event_id).occurred_at
                else datetime.max.replace(tzinfo=timezone.utc)
            ),
        )
        edges.append(
            SignalGraphEdgeOut(
                id=edge_id,
                from_node_id=from_entity_id,
                to_node_id=to_entity_id,
                type=f"{source_role}__{target_role}",
                label=_edge_label_for_roles(source_role, target_role),
                weight=data["weight"],
                evidence_event_ids=event_ids_sorted,
                first_seen_at=data["first_seen_at"],
                last_seen_at=data["last_seen_at"],
                attrs={
                    "source_role": source_role,
                    "target_role": target_role,
                },
            )
        )

    def _story_actors(
        participants: list[SignalTimelineParticipantOut],
        preferred_roles: set[str],
    ) -> list[SignalStoryActorOut]:
        selected = [p for p in participants if p.role.lower() in preferred_roles]
        if not selected:
            selected = participants
        out: list[SignalStoryActorOut] = []
        seen: set[uuid.UUID] = set()
        for participant in selected:
            if participant.entity_id in seen:
                continue
            seen.add(participant.entity_id)
            out.append(
                SignalStoryActorOut(
                    entity_id=participant.entity_id,
                    name=participant.name,
                    node_type=participant.node_type,
                    roles=[participant.role],
                    event_count=len(entity_event_sets.get(participant.entity_id, set())),
                )
            )
        return sorted(out, key=_actor_sort_key)

    first_timeline = timeline[0] if timeline else None
    last_timeline = timeline[-1] if timeline else None
    started_at = first_timeline.occurred_at if first_timeline else signal.period_start
    ended_at = last_timeline.occurred_at if last_timeline else signal.period_end

    started_from_entities = _story_actors(
        first_timeline.participants if first_timeline else [],
        _INITIATOR_ROLES,
    )
    flow_targets = _story_actors(
        last_timeline.participants if last_timeline else [],
        _TARGET_ROLES,
    )

    # BFS expansion: discover connected entities via GraphNode/GraphEdge
    expanded_nodes: list[ExpandedNodeOut] = []
    expansion_edges: list[ExpansionEdgeOut] = []
    direct_entity_ids = set(entity_profiles.keys())

    if direct_entity_ids:
        gn_stmt = select(GraphNode).where(GraphNode.entity_id.in_(direct_entity_ids))
        direct_graph_nodes = list((await session.execute(gn_stmt)).scalars().all())
        direct_node_ids = {gn.id for gn in direct_graph_nodes}

        if direct_node_ids:
            edge_stmt = select(GraphEdge).where(
                or_(
                    GraphEdge.from_node_id.in_(direct_node_ids),
                    GraphEdge.to_node_id.in_(direct_node_ids),
                )
            ).limit(100)
            bfs_edges = list((await session.execute(edge_stmt)).scalars().all())

            discovered_node_ids: set[uuid.UUID] = set()
            for edge in bfs_edges:
                if edge.from_node_id not in direct_node_ids:
                    discovered_node_ids.add(edge.from_node_id)
                if edge.to_node_id not in direct_node_ids:
                    discovered_node_ids.add(edge.to_node_id)

            disc_node_map: dict[uuid.UUID, 'GraphNode'] = {}
            if discovered_node_ids:
                disc_stmt = select(GraphNode).where(GraphNode.id.in_(discovered_node_ids))
                disc_nodes = list((await session.execute(disc_stmt)).scalars().all())
                disc_node_map = {gn.id: gn for gn in disc_nodes}

                disc_entity_ids = {gn.entity_id for gn in disc_nodes}
                disc_ent_stmt = select(Entity).where(Entity.id.in_(disc_entity_ids))
                disc_entities = {e.id: e for e in (await session.execute(disc_ent_stmt)).scalars().all()}

                for gn in disc_nodes:
                    entity = disc_entities.get(gn.entity_id)
                    expanded_nodes.append(ExpandedNodeOut(
                        id=gn.id,
                        entity_id=gn.entity_id,
                        label=gn.label,
                        node_type=gn.node_type,
                        source_connector=(entity.attrs or {}).get("source_connector") if entity else None,
                        attrs=gn.attrs or {},
                        is_direct_participant=False,
                    ))

            all_node_map = {gn.id: gn for gn in direct_graph_nodes}
            all_node_map.update(disc_node_map)

            for edge in bfs_edges:
                from_gn = all_node_map.get(edge.from_node_id)
                to_gn = all_node_map.get(edge.to_node_id)
                if from_gn and to_gn:
                    expansion_edges.append(ExpansionEdgeOut(
                        id=edge.id,
                        from_entity_id=from_gn.entity_id,
                        to_entity_id=to_gn.entity_id,
                        edge_type=edge.type,
                        weight=edge.weight,
                        attrs=edge.attrs or {},
                    ))

    # Cluster expansion: find entities sharing cluster_id
    cluster_map: dict[uuid.UUID, list[ClusterEntityOut]] = defaultdict(list)
    cluster_ids = {e.cluster_id for e in entity_profiles.values() if e.cluster_id is not None}
    if cluster_ids:
        cluster_stmt = select(Entity).where(
            Entity.cluster_id.in_(cluster_ids),
            ~Entity.id.in_(direct_entity_ids),
        ).limit(50)
        cluster_entities_list = list((await session.execute(cluster_stmt)).scalars().all())
        for ce in cluster_entities_list:
            cluster_map[ce.cluster_id].append(ClusterEntityOut(
                entity_id=ce.id, name=ce.name, node_type=ce.type,
            ))

    involved_profiles = [
        SignalInvolvedEntityProfileOut(
            entity_id=entity.id,
            name=entity.name,
            node_type=entity.type,
            identifiers=entity.identifiers or {},
            attrs=entity.attrs or {},
            photo_url=_extract_photo_url(entity.attrs or {}),
            roles_in_signal=[
                SignalInvolvedEntityRoleOut(
                    code=role,
                    label=_role_label(role),
                    count_in_signal=count,
                )
                for role, count in sorted(
                    role_counts.get(entity.id, {}).items(),
                    key=lambda item: (-item[1], item[0]),
                )
            ],
            event_count=len(entity_event_sets.get(entity.id, set())),
            is_direct_participant=True,
            cluster_entities=cluster_map.get(entity.cluster_id, []) if entity.cluster_id else [],
        )
        for entity in involved_entities
    ]

    fallback_reason = None
    has_minimum_network = len(involved_profiles) >= 2 and len(edges) > 0
    if not has_minimum_network:
        if not events:
            fallback_reason = "events_not_found"
        elif len(involved_profiles) < 2:
            fallback_reason = "insufficient_entities"
        elif not edges:
            fallback_reason = "no_relationship_edges"

    if mode == "preview":
        timeline = timeline[:8]
        edges = edges[:20]
        involved_profiles = involved_profiles[:20]
        nodes = nodes[:30]

    return SignalGraphResponse(
        signal=signal_out,
        pattern_story=SignalPatternStoryOut(
            pattern_label=signal.typology.name,
            started_at=started_at,
            ended_at=ended_at,
            started_from_entities=started_from_entities,
            flow_targets=flow_targets,
            why_flagged=why_flagged,
        ),
        overview=SignalGraphOverviewOut(
            nodes=nodes,
            edges=edges,
            expanded_nodes=expanded_nodes,
            expansion_edges=expansion_edges,
        ),
        timeline=timeline,
        involved_entities=involved_profiles,
        diagnostics=SignalGraphDiagnosticsOut(
            events_total=len(parsed_event_ids),
            events_loaded=len(events),
            events_missing=max(0, len(parsed_event_ids) - len(events)),
            participants_total=len(participant_rows),
            unique_entities=len(involved_profiles),
            has_minimum_network=has_minimum_network,
            fallback_reason=fallback_reason,
        ),
    )


async def get_evidence_package_by_id(
    session: AsyncSession,
    evidence_package_id: uuid.UUID,
) -> Optional[EvidencePackage]:
    stmt = select(EvidencePackage).where(EvidencePackage.id == evidence_package_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_signal_evidence_page(
    session: AsyncSession,
    signal_id: uuid.UUID,
    offset: int = 0,
    limit: int = 10,
    sort: str = "occurred_at_desc",
) -> Optional[dict]:
    signal = await get_signal_by_id(session, signal_id)
    if signal is None:
        return None

    parsed_event_ids = _to_uuid_list(signal.event_ids or [])
    if not parsed_event_ids:
        return {
            "signal_id": str(signal.id),
            "total": 0,
            "offset": offset,
            "limit": limit,
            "items": [],
        }

    event_stmt = select(Event).where(Event.id.in_(parsed_event_ids))
    event_result = await session.execute(event_stmt)
    events = list(event_result.scalars().all())
    event_map: dict[uuid.UUID, Event] = {e.id: e for e in events}

    event_ref_descriptions = {}
    for ref in signal.evidence_refs or []:
        if ref.get("ref_type") == "event" and ref.get("ref_id"):
            event_ref_descriptions[str(ref.get("ref_id"))] = ref.get("description")

    evidence_reason = (
        "Compoe o cluster temporal e o somatorio do sinal"
        if signal.typology and signal.typology.code == "T03"
        else "Evento referenciado como evidencia do sinal"
    )

    items = []
    for event_id in parsed_event_ids:
        event = event_map.get(event_id)
        if event is None:
            continue

        attrs = event.attrs or {}
        catmat_group = _normalize_missing_text(
            attrs.get("catmat_group") or attrs.get("catmat_code")
        )
        description = (
            event_ref_descriptions.get(str(event.id))
            or event.description
            or f"Evento {event.id}"
        )
        modality = attrs.get("modality") or event.subtype or "Nao informado"

        items.append(
            {
                "event_id": str(event.id),
                "occurred_at": event.occurred_at,
                "value_brl": event.value_brl,
                "description": description,
                "source_connector": event.source_connector,
                "source_id": event.source_id,
                "modality": modality,
                "catmat_group": catmat_group,
                "evidence_reason": evidence_reason,
            }
        )

    if sort == "value_desc":
        items.sort(key=lambda x: (x["value_brl"] is None, -(x["value_brl"] or 0)))
    elif sort == "value_asc":
        items.sort(key=lambda x: (x["value_brl"] is None, x["value_brl"] or 0))
    elif sort == "occurred_at_asc":
        items.sort(
            key=lambda x: x["occurred_at"] or datetime.max.replace(tzinfo=timezone.utc)
        )
        items.sort(key=lambda x: x["occurred_at"] is None)
    else:
        # Default: latest first, keeping missing dates at the end.
        items.sort(
            key=lambda x: x["occurred_at"] or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )
        items.sort(key=lambda x: x["occurred_at"] is None)

    total = len(items)
    paginated = items[offset : offset + limit]
    return {
        "signal_id": str(signal.id),
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": paginated,
    }


async def get_radar_v2_signal_preview(
    session: AsyncSession,
    signal_id: uuid.UUID,
    *,
    evidence_limit: int = 10,
) -> Optional[dict]:
    signal_detail = await get_signal_detail(session, signal_id)
    if signal_detail is None:
        return None

    signal_graph = await get_signal_graph(session, signal_id, mode="preview")
    if signal_graph is None:
        return None
    signal_evidence = await get_signal_evidence_page(
        session,
        signal_id=signal_id,
        offset=0,
        limit=evidence_limit,
        sort="occurred_at_desc",
    )

    return {
        "signal": signal_detail,
        "graph": signal_graph,
        "evidence": signal_evidence or {
            "signal_id": str(signal_id),
            "total": 0,
            "offset": 0,
            "limit": evidence_limit,
            "items": [],
        },
    }


async def get_radar_v2_case_preview(
    session: AsyncSession,
    case_id: uuid.UUID,
) -> Optional[dict]:
    case = await get_case_by_id(session, case_id)
    if case is None:
        return None

    attrs = case.attrs or {}
    signal_rows = []
    entity_names = attrs.get("entity_names", [])
    for item in case.items:
        signal = item.signal
        if signal is None or signal.typology is None:
            continue
        signal_rows.append(
            {
                "id": str(signal.id),
                "typology_code": signal.typology.code,
                "typology_name": signal.typology.name,
                "severity": signal.severity,
                "data_completeness": signal.data_completeness,
                "title": signal.title,
                "summary": signal.summary,
                "period_start": signal.period_start,
                "period_end": signal.period_end,
                "entity_count": len(signal.entity_ids or []),
                "event_count": len(signal.event_ids or []),
            }
        )

    signal_rows.sort(
        key=lambda row: (
            -_SEVERITY_TO_SCORE.get(str(row["severity"]), 0.0),
            -(float(row["data_completeness"] or 0)),
        )
    )
    case_graph = await get_case_graph(session, case_id, depth=1, limit=120)
    if case_graph is None:
        return None

    return {
        "case": {
            "id": str(case.id),
            "title": case.title,
            "status": case.status,
            "severity": case.severity,
            "summary": case.summary,
            "entity_names": entity_names,
            "signal_count": len(signal_rows),
            "period_start": attrs.get("period_start"),
            "period_end": attrs.get("period_end"),
            "total_value_brl": attrs.get("total_value_brl"),
            "created_at": case.created_at,
        },
        "graph": case_graph,
        "top_signals": signal_rows[:10],
    }


async def get_radar_v2_coverage(session: AsyncSession) -> RadarV2CoverageResponse:
    analytics = await get_analytical_coverage(session)
    apt_count = sum(1 for item in analytics if item.get("apt"))
    with_signals_30d = sum(1 for item in analytics if int(item.get("signals_30d") or 0) > 0)
    blocked_count = sum(1 for item in analytics if not item.get("apt"))
    return RadarV2CoverageResponse(
        summary=RadarV2CoverageSummaryOut(
            apt_count=apt_count,
            with_signals_30d=with_signals_30d,
            blocked_count=blocked_count,
            total_typologies=len(analytics),
        ),
        items=analytics,
    )


async def replay_signal(
    session: AsyncSession,
    signal_id: uuid.UUID,
) -> Optional[SignalReplayOut]:
    signal = await get_signal_by_id(session, signal_id)
    if signal is None:
        return None

    package = None
    if signal.evidence_package_id:
        package = await get_evidence_package_by_id(session, signal.evidence_package_id)

    replay_hash = build_signal_replay_hash(signal, package)
    stored_signature = package.signature if package else None

    return SignalReplayOut(
        signal_id=signal.id,
        replay_hash=replay_hash,
        stored_signature=stored_signature,
        deterministic_match=(stored_signature == replay_hash if stored_signature else False),
        checked_at=datetime.now(timezone.utc),
    )


async def get_signal_quality_metrics(session: AsyncSession) -> dict:
    total_signals = int(
        (await session.execute(select(func.count()).select_from(RiskSignal))).scalar_one() or 0
    )
    high_critical_signals = int(
        (
            await session.execute(
                select(func.count())
                .select_from(RiskSignal)
                .where(RiskSignal.severity.in_(["high", "critical"]))
            )
        ).scalar_one()
        or 0
    )
    with_explanation = int(
        (
            await session.execute(
                select(func.count())
                .select_from(RiskSignal)
                .where(
                    RiskSignal.severity.in_(["high", "critical"]),
                    RiskSignal.explanation_md.isnot(None),
                )
            )
        ).scalar_one()
        or 0
    )
    high_critical_explained_and_paginable = int(
        (
            await session.execute(
                select(func.count())
                .select_from(RiskSignal)
                .where(
                    RiskSignal.severity.in_(["high", "critical"]),
                    RiskSignal.explanation_md.isnot(None),
                    func.jsonb_array_length(RiskSignal.event_ids) > 0,
                )
            )
        ).scalar_one()
        or 0
    )
    with_event_ids = int(
        (
            await session.execute(
                select(func.count())
                .select_from(RiskSignal)
                .where(func.jsonb_array_length(RiskSignal.event_ids) > 0)
            )
        ).scalar_one()
        or 0
    )
    with_listed_evidence = int(
        (
            await session.execute(
                select(func.count())
                .select_from(RiskSignal)
                .where(func.jsonb_array_length(RiskSignal.evidence_refs) > 0)
            )
        ).scalar_one()
        or 0
    )
    unknown_titles = int(
        (
            await session.execute(
                select(func.count())
                .select_from(RiskSignal)
                .where(
                    or_(
                        RiskSignal.title.ilike("%unknown%"),
                        RiskSignal.title.ilike("%sem classificacao%"),
                        RiskSignal.title.ilike("%sem classificação%"),
                    )
                )
            )
        ).scalar_one()
        or 0
    )

    explanation_coverage_pct = round(
        (with_explanation / high_critical_signals) * 100, 2
    ) if high_critical_signals else 0.0
    evidence_paginable_pct = round(
        (with_event_ids / total_signals) * 100, 2
    ) if total_signals else 0.0
    high_critical_explained_and_paginable_pct = round(
        (high_critical_explained_and_paginable / high_critical_signals) * 100, 2
    ) if high_critical_signals else 0.0

    return {
        "total_signals": total_signals,
        "high_critical_signals": high_critical_signals,
        "signals_with_explanation": with_explanation,
        "high_critical_explained_and_paginable": high_critical_explained_and_paginable,
        "signals_with_event_ids": with_event_ids,
        "signals_with_listed_evidence": with_listed_evidence,
        "titles_with_unknown": unknown_titles,
        "explanation_coverage_pct": explanation_coverage_pct,
        "evidence_paginable_pct": evidence_paginable_pct,
        "high_critical_explained_and_paginable_pct": high_critical_explained_and_paginable_pct,
    }


# --- Baseline queries ---


async def get_events_for_baseline(
    session: AsyncSession,
    window_start: datetime,
    window_end: datetime,
    event_type: str,
) -> list[Event]:
    """Get events within a time window for baseline computation."""
    stmt = (
        select(Event)
        .where(
            Event.type == event_type,
            Event.occurred_at >= window_start,
            Event.occurred_at <= window_end,
        )
        .order_by(Event.occurred_at)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_baseline(
    session: AsyncSession,
    baseline_type: str,
    scope_key: str,
    _cache: dict | None = None,
) -> Optional[dict]:
    """Get the latest baseline metrics for a given type and scope.

    Returns the metrics dict (percentiles) or None if not found.
    Falls back to 'national::all' scope if specific scope not found.

    Pass a dict as ``_cache`` to enable per-execution caching across
    repeated calls within the same typology run, avoiding redundant
    DB round-trips for the same (baseline_type, scope_key) pair.
    """
    cache_key = (baseline_type, scope_key)
    if _cache is not None and cache_key in _cache:
        return _cache[cache_key]

    stmt = (
        select(BaselineSnapshot)
        .where(
            BaselineSnapshot.baseline_type == baseline_type,
            BaselineSnapshot.scope_key == scope_key,
        )
        .order_by(BaselineSnapshot.window_end.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    snapshot = result.scalar_one_or_none()

    if snapshot is not None:
        metrics = {
            "sample_size": snapshot.sample_size,
            "scope_key": snapshot.scope_key,
            **snapshot.metrics,
        }
        if _cache is not None:
            _cache[cache_key] = metrics
        return metrics

    # Fallback to national scope
    if scope_key != "national::all":
        return await get_baseline(session, baseline_type, "national::all", _cache=_cache)

    if _cache is not None:
        _cache[cache_key] = None
    return None


# --- Case queries ---


async def get_cases_paginated(
    session: AsyncSession,
    offset: int = 0,
    limit: int = 20,
    severity: Optional[str] = None,
) -> tuple[list[Case], int]:
    """Get paginated cases with optional severity filter."""
    stmt = (
        select(Case)
        .options(
            selectinload(Case.items)
            .selectinload(CaseItem.signal)
            .selectinload(RiskSignal.typology)
        )
        .order_by(Case.created_at.desc())
    )
    count_stmt = select(func.count()).select_from(Case)

    if severity:
        stmt = stmt.where(Case.severity == severity)
        count_stmt = count_stmt.where(Case.severity == severity)

    total = (await session.execute(count_stmt)).scalar_one()
    result = await session.execute(stmt.offset(offset).limit(limit))
    cases = list(result.scalars().all())

    return cases, total


def _risk_signal_matches_filters(
    signal: RiskSignal,
    *,
    typology_code: Optional[str],
    severity: Optional[str],
    period_from: Optional[datetime],
    period_to: Optional[datetime],
    allowed_typology_codes: set[str] | None,
) -> bool:
    current_typology_code = signal.typology.code if signal.typology else None
    if typology_code and current_typology_code != typology_code:
        return False
    if severity and signal.severity != severity:
        return False
    if allowed_typology_codes is not None and current_typology_code not in allowed_typology_codes:
        return False
    if period_from and signal.period_end and signal.period_end < period_from:
        return False
    if period_to and signal.period_start and signal.period_start > period_to:
        return False
    return True


async def get_radar_v2_cases(
    session: AsyncSession,
    *,
    offset: int = 0,
    limit: int = 20,
    typology_code: Optional[str] = None,
    severity: Optional[str] = None,
    period_from: Optional[datetime] = None,
    period_to: Optional[datetime] = None,
    corruption_type: Optional[str] = None,
    sphere: Optional[str] = None,
) -> tuple[list[RadarV2CaseListItemOut], int]:
    """Paginated case list with SQL-level filtering.

    Filters are pushed to SQL so only matching rows are fetched — O(page_size)
    instead of O(N_total).
    """
    allowed_typology_codes: set[str] | None = None
    if corruption_type or sphere:
        from shared.typologies.factor_metadata import get_typology_codes_for_filter

        allowed = get_typology_codes_for_filter(
            corruption_type=corruption_type,
            sphere=sphere,
        )
        allowed_typology_codes = set(allowed or [])

    # ── Build signal filter subquery ──────────────────────────────────────
    # Find case_ids that have at least one matching signal.
    sig_filter = (
        select(CaseItem.case_id)
        .join(RiskSignal, CaseItem.signal_id == RiskSignal.id)
        .join(Typology, RiskSignal.typology_id == Typology.id)
    )

    conditions = []
    if typology_code:
        conditions.append(Typology.code == typology_code)
    if severity:
        conditions.append(RiskSignal.severity == severity)
    if period_from:
        conditions.append(RiskSignal.period_end >= period_from)
    if period_to:
        conditions.append(RiskSignal.period_start <= period_to)
    if allowed_typology_codes is not None:
        conditions.append(Typology.code.in_(allowed_typology_codes))

    if conditions:
        sig_filter = sig_filter.where(*conditions)

    matching_case_ids = sig_filter.distinct().subquery()

    # ── Count total matching cases ────────────────────────────────────────
    count_stmt = select(func.count()).select_from(matching_case_ids)
    total = int((await session.execute(count_stmt)).scalar_one())

    if total == 0:
        return [], 0

    # ── Fetch paginated case IDs (ordered by created_at desc) ─────────────
    paged_ids_stmt = (
        select(Case.id)
        .where(Case.id.in_(select(matching_case_ids.c.case_id)))
        .order_by(Case.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    paged_ids = list((await session.execute(paged_ids_stmt)).scalars().all())

    if not paged_ids:
        return [], total

    # ── Aggregate signal stats for paginated cases only ───────────────────
    stats_stmt = (
        select(
            CaseItem.case_id,
            func.count(RiskSignal.id).label("signal_count"),
            func.array_agg(func.distinct(Typology.code)).label("typology_codes"),
            func.min(RiskSignal.period_start).label("period_start"),
            func.max(RiskSignal.period_end).label("period_end"),
        )
        .join(RiskSignal, CaseItem.signal_id == RiskSignal.id)
        .join(Typology, RiskSignal.typology_id == Typology.id)
        .where(CaseItem.case_id.in_(paged_ids))
    )
    stats_stmt = stats_stmt.group_by(CaseItem.case_id)
    stats_rows = (await session.execute(stats_stmt)).all()
    stats_map = {row.case_id: row for row in stats_rows}

    # ── Collect entity_ids per case (O(page_size)) ────────────────────────
    eid_stmt = (
        select(CaseItem.case_id, RiskSignal.entity_ids)
        .join(RiskSignal, CaseItem.signal_id == RiskSignal.id)
        .join(Typology, RiskSignal.typology_id == Typology.id)
        .where(CaseItem.case_id.in_(paged_ids))
    )

    eid_rows = (await session.execute(eid_stmt)).all()
    entity_sets: dict[uuid.UUID, set[str]] = {}
    for row in eid_rows:
        s = entity_sets.setdefault(row.case_id, set())
        for eid in row.entity_ids or []:
            s.add(str(eid))
    entity_map = {cid: len(eids) for cid, eids in entity_sets.items()}

    # ── Fetch Case objects for metadata ───────────────────────────────────
    cases_stmt = (
        select(Case)
        .where(Case.id.in_(paged_ids))
        .order_by(Case.created_at.desc())
    )
    case_objs = list((await session.execute(cases_stmt)).scalars().all())

    # ── Build response ────────────────────────────────────────────────────
    items: list[RadarV2CaseListItemOut] = []
    for case in case_objs:
        stats = stats_map.get(case.id)
        items.append(
            RadarV2CaseListItemOut(
                id=case.id,
                title=case.title,
                status=case.status,
                severity=SignalSeverity(case.severity),
                summary=case.summary,
                signal_count=stats.signal_count if stats else 0,
                entity_count=entity_map.get(case.id, 0),
                typology_codes=sorted(stats.typology_codes or []) if stats else [],
                period_start=stats.period_start if stats else None,
                period_end=stats.period_end if stats else None,
                created_at=case.created_at,
            )
        )

    return items, total


async def get_dossier_summary(
    session: AsyncSession,
    case_id: uuid.UUID,
) -> dict | None:
    """Full dossier summary for a case: chapters by typology, entity roster, legal hypotheses."""
    from shared.models.orm import CaseItem, Typology, LegalViolationHypothesis

    # Fetch case
    case_stmt = select(Case).where(Case.id == case_id)
    case = (await session.execute(case_stmt)).scalar_one_or_none()
    if case is None:
        return None

    # Fetch all signals for this case with typology info
    signals_stmt = (
        select(
            RiskSignal.id,
            RiskSignal.typology_id,
            RiskSignal.severity,
            RiskSignal.data_completeness,
            RiskSignal.title,
            RiskSignal.summary,
            RiskSignal.period_start,
            RiskSignal.period_end,
            RiskSignal.entity_ids,
            RiskSignal.factors,
            Typology.code.label("typology_code"),
            Typology.name.label("typology_name"),
        )
        .join(CaseItem, CaseItem.signal_id == RiskSignal.id)
        .join(Typology, RiskSignal.typology_id == Typology.id)
        .where(CaseItem.case_id == case_id)
        .order_by(Typology.code, RiskSignal.data_completeness.desc())
    )
    sig_rows = (await session.execute(signals_stmt)).all()

    # Group signals by typology → chapters
    from collections import defaultdict
    chapters_map: dict[str, dict] = {}
    for r in sig_rows:
        code = r.typology_code
        if code not in chapters_map:
            chapters_map[code] = {
                "typology_code": code,
                "typology_name": r.typology_name,
                "signal_count": 0,
                "max_severity": r.severity,
                "total_value_brl": 0.0,
                "period_start": None,
                "period_end": None,
                "top_signal_summary": r.summary or r.title,
                "signal_ids": [],
            }
        ch = chapters_map[code]
        ch["signal_count"] += 1
        ch["signal_ids"].append(str(r.id))

        # Update max severity
        sev_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        if sev_order.get(r.severity, 0) > sev_order.get(ch["max_severity"], 0):
            ch["max_severity"] = r.severity

        # Accumulate value from factors (check all known value keys)
        if r.factors and isinstance(r.factors, dict):
            val = (
                r.factors.get("total_value_brl")
                or r.factors.get("observed_total_brl")
                or r.factors.get("contract_value_brl")
                or r.factors.get("intra_community_value")
                or 0
            )
            if isinstance(val, (int, float)):
                ch["total_value_brl"] += val

        # Expand period
        if r.period_start:
            if ch["period_start"] is None or r.period_start < ch["period_start"]:
                ch["period_start"] = r.period_start
        if r.period_end:
            if ch["period_end"] is None or r.period_end > ch["period_end"]:
                ch["period_end"] = r.period_end

    chapters = sorted(chapters_map.values(), key=lambda c: -{"critical": 4, "high": 3, "medium": 2, "low": 1}.get(c["max_severity"], 0))

    # Serialize datetimes in chapters
    for ch in chapters:
        if ch["period_start"]:
            ch["period_start"] = ch["period_start"].isoformat()
        if ch["period_end"]:
            ch["period_end"] = ch["period_end"].isoformat()

    # Entity roster
    entity_ids: set[str] = set()
    for r in sig_rows:
        for eid in r.entity_ids or []:
            entity_ids.add(str(eid))

    entity_roster = []
    if entity_ids:
        from shared.models.orm import Entity
        entity_stmt = select(Entity).where(Entity.id.in_([uuid.UUID(e) for e in entity_ids]))
        entities = (await session.execute(entity_stmt)).scalars().all()
        entity_roster = [
            {
                "id": str(e.id),
                "type": e.type,
                "name": e.name,
                "identifiers": e.identifiers or {},
            }
            for e in entities
        ]

    # Legal hypotheses
    legal_stmt = (
        select(LegalViolationHypothesis)
        .where(LegalViolationHypothesis.case_id == case_id)
    )
    legal_rows = (await session.execute(legal_stmt)).scalars().all()
    legal_hypotheses = [
        {
            "id": f"{case_id}-{i}",
            "law": lh.law_name,
            "article": lh.article,
            "violation_type": lh.violation_type,
            "description": None,
            "confidence": lh.confidence,
            "signal_cluster": lh.signal_cluster or [],
        }
        for i, lh in enumerate(legal_rows)
    ]

    # Related cases (share entity names)
    entity_names = list((case.attrs or {}).get("entity_names", []))
    related_cases = []
    if entity_names:
        from sqlalchemy import text
        related_stmt = text("""
            SELECT c.id, c.title, c.severity, c.case_type, c.created_at
            FROM "case" c,
            LATERAL jsonb_array_elements_text(COALESCE(c.attrs->'entity_names', '[]'::jsonb)) AS name
            WHERE c.id != :case_id
              AND name = ANY(:entity_names)
            GROUP BY c.id, c.title, c.severity, c.case_type, c.created_at
            ORDER BY c.created_at DESC
            LIMIT 5
        """)
        result = await session.execute(
            related_stmt,
            {"case_id": case_id, "entity_names": entity_names},
        )
        related_cases = [
            {
                "id": str(r.id),
                "title": r.title,
                "severity": r.severity,
                "case_type": r.case_type,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in result.all()
        ]

    return {
        "case": {
            "id": str(case.id),
            "title": case.title,
            "status": case.status,
            "severity": case.severity,
            "summary": case.summary,
            "created_at": case.created_at.isoformat() if case.created_at else None,
            "entity_names": entity_names,
            "total_value_brl": sum(ch["total_value_brl"] for ch in chapters) or (case.attrs or {}).get("total_value_brl"),
            "signal_count": len(sig_rows),
            "entity_count": len(entity_ids),
        },
        "chapters": chapters,
        "entity_roster": entity_roster,
        "legal_hypotheses": legal_hypotheses,
        "related_cases": related_cases,
    }


# --- Graph queries ---


async def get_graph_neighborhood(
    session: AsyncSession,
    entity_id: uuid.UUID,
    depth: int = 1,
    limit: int = 100,
) -> NeighborhoodResponse:
    """Get graph neighborhood around an entity, up to given depth.

    Uses iterative expansion from center node through graph edges.
    """
    # Find center node
    center_stmt = select(GraphNode).where(GraphNode.entity_id == entity_id)
    center_result = await session.execute(center_stmt)
    center_node = center_result.scalar_one_or_none()

    entity_stmt = select(Entity).where(Entity.id == entity_id)
    entity = (await session.execute(entity_stmt)).scalar_one_or_none()

    entity_events_stmt = select(func.count(func.distinct(EventParticipant.event_id))).where(
        EventParticipant.entity_id == entity_id
    )
    entity_event_count = int((await session.execute(entity_events_stmt)).scalar_one() or 0)

    entity_event_ids_subq = (
        select(EventParticipant.event_id)
        .where(EventParticipant.entity_id == entity_id)
        .subquery()
    )
    co_count_stmt = select(func.count(func.distinct(EventParticipant.entity_id))).where(
        EventParticipant.event_id.in_(select(entity_event_ids_subq.c.event_id)),
        EventParticipant.entity_id != entity_id,
    )
    co_participant_count = int((await session.execute(co_count_stmt)).scalar_one() or 0)

    co_participants_stmt = (
        select(
            Entity.id,
            Entity.name,
            Entity.type,
            func.count(func.distinct(EventParticipant.event_id)).label("shared_events"),
        )
        .join(EventParticipant, EventParticipant.entity_id == Entity.id)
        .where(
            EventParticipant.event_id.in_(select(entity_event_ids_subq.c.event_id)),
            Entity.id != entity_id,
        )
        .group_by(Entity.id, Entity.name, Entity.type)
        .order_by(func.count(func.distinct(EventParticipant.event_id)).desc(), Entity.name)
        .limit(10)
    )
    co_rows = (await session.execute(co_participants_stmt)).all()
    co_participants = [
        CoParticipantOut(
            entity_id=row.id,
            label=row.name,
            node_type=row.type,
            shared_events=int(row.shared_events or 0),
        )
        for row in co_rows
    ]

    if entity_event_count == 0:
        reason = "no_events_for_entity"
    elif co_participant_count == 0:
        reason = "no_coparticipants_or_er_not_run"
    elif center_node is None:
        reason = "er_not_materialized"
    else:
        reason = "graph_available"

    diagnostics = GraphDiagnosticsOut(
        graph_materialized=center_node is not None,
        entity_event_count=entity_event_count,
        co_participant_count=co_participant_count,
        reason=reason,
    )
    virtual_center_node = (
        VirtualCenterNodeOut(
            entity_id=entity.id,
            label=entity.name,
            node_type=entity.type,
        )
        if entity is not None
        else None
    )

    # ── Fallback: graph not materialized but co_participants exist ──────────────
    # Build virtual nodes + edges from co-occurrence data so the graph is not empty.
    if center_node is None:
        virtual_nodes: list[GraphNodeOut] = []
        virtual_edges: list[GraphEdgeOut] = []

        if entity is not None and co_participants:
            # Synthetic center node id (deterministic from entity_id)
            center_virtual_id = uuid.uuid5(uuid.UUID("00000000-0000-0000-0000-000000000001"), str(entity_id))
            virtual_nodes.append(GraphNodeOut(
                id=center_virtual_id,
                entity_id=entity_id,
                label=entity.name,
                node_type=entity.type,
                attrs={},
            ))
            for cp in co_participants:
                cp_virtual_id = uuid.uuid5(uuid.UUID("00000000-0000-0000-0000-000000000001"), str(cp.entity_id))
                virtual_nodes.append(GraphNodeOut(
                    id=cp_virtual_id,
                    entity_id=cp.entity_id,
                    label=cp.label,
                    node_type=cp.node_type,
                    attrs={"shared_events": cp.shared_events},
                ))
                edge_virtual_id = uuid.uuid5(uuid.UUID("00000000-0000-0000-0000-000000000002"), f"{center_virtual_id}-{cp_virtual_id}")
                virtual_edges.append(GraphEdgeOut(
                    id=edge_virtual_id,
                    from_node_id=center_virtual_id,
                    to_node_id=cp_virtual_id,
                    type="coparticipacao_evento",
                    weight=float(cp.shared_events),
                    edge_strength="strong" if cp.shared_events >= 3 else "weak",
                    verification_method="co_occurrence",
                    verification_confidence=min(0.9, 0.2 + cp.shared_events * 0.07),
                    attrs={"shared_events": cp.shared_events, "virtual": True},
                ))

            return NeighborhoodResponse(
                center_node_id=center_virtual_id,
                nodes=virtual_nodes,
                edges=virtual_edges,
                depth=depth,
                truncated=False,
                diagnostics=diagnostics,
                virtual_center_node=virtual_center_node,
                co_participants=co_participants,
            )

        return NeighborhoodResponse(
            center_node_id=entity_id,
            nodes=[],
            edges=[],
            depth=depth,
            truncated=False,
            diagnostics=diagnostics,
            virtual_center_node=virtual_center_node,
            co_participants=co_participants,
        )

    # ── BFS expansion through graph edges ──────────────────────────────────────
    visited_node_ids: set[uuid.UUID] = {center_node.id}
    frontier: set[uuid.UUID] = {center_node.id}
    all_edges: list[GraphEdge] = []

    for _ in range(depth):
        if not frontier:
            break

        edge_stmt = select(GraphEdge).where(
            (GraphEdge.from_node_id.in_(frontier))
            | (GraphEdge.to_node_id.in_(frontier))
        )
        edge_result = await session.execute(edge_stmt)
        edges = list(edge_result.scalars().all())
        all_edges.extend(edges)

        new_frontier: set[uuid.UUID] = set()
        for e in edges:
            if e.from_node_id not in visited_node_ids:
                new_frontier.add(e.from_node_id)
            if e.to_node_id not in visited_node_ids:
                new_frontier.add(e.to_node_id)

        visited_node_ids |= new_frontier
        frontier = new_frontier

        if len(visited_node_ids) >= limit:
            break

    truncated = len(visited_node_ids) >= limit

    # Load all nodes
    node_stmt = select(GraphNode).where(GraphNode.id.in_(visited_node_ids)).limit(limit)
    node_result = await session.execute(node_stmt)
    nodes = list(node_result.scalars().all())

    # Deduplicate edges
    seen_edges: set[uuid.UUID] = set()
    unique_edges: list[GraphEdge] = []
    for e in all_edges:
        if e.id not in seen_edges:
            seen_edges.add(e.id)
            unique_edges.append(e)

    # ── Cluster siblings: add same-cluster entities with synthetic edges ────────
    # Connects all representations of the same real-world entity across sources.
    extra_nodes: list[GraphNodeOut] = []
    extra_edges: list[GraphEdgeOut] = []

    if entity is not None and entity.cluster_id is not None:
        sibling_stmt = (
            select(Entity, GraphNode)
            .join(GraphNode, GraphNode.entity_id == Entity.id, isouter=True)
            .where(
                Entity.cluster_id == entity.cluster_id,
                Entity.id != entity_id,
            )
        )
        sibling_rows = (await session.execute(sibling_stmt)).all()
        existing_entity_ids = {n.entity_id for n in nodes}

        for sibling_entity, sibling_node in sibling_rows:
            if sibling_entity.id in existing_entity_ids:
                continue
            # Use real GraphNode id if materialized, else synthetic
            if sibling_node is not None:
                sibling_gid = sibling_node.id
                extra_nodes.append(GraphNodeOut(
                    id=sibling_gid,
                    entity_id=sibling_entity.id,
                    label=sibling_node.label,
                    node_type=sibling_node.node_type,
                    attrs=sibling_node.attrs,
                ))
            else:
                sibling_gid = uuid.uuid5(uuid.UUID("00000000-0000-0000-0000-000000000001"), str(sibling_entity.id))
                extra_nodes.append(GraphNodeOut(
                    id=sibling_gid,
                    entity_id=sibling_entity.id,
                    label=sibling_entity.name,
                    node_type=sibling_entity.type,
                    attrs={},
                ))
            existing_entity_ids.add(sibling_entity.id)

            edge_id = uuid.uuid5(uuid.UUID("00000000-0000-0000-0000-000000000003"), f"{center_node.id}-{sibling_gid}")
            extra_edges.append(GraphEdgeOut(
                id=edge_id,
                from_node_id=center_node.id,
                to_node_id=sibling_gid,
                type="same_cluster_entity",
                weight=3.0,
                edge_strength="strong",
                verification_method="cluster_resolution",
                verification_confidence=0.95,
                attrs={"cluster_id": str(entity.cluster_id), "virtual": True},
            ))

    out_nodes = [
        GraphNodeOut(id=n.id, entity_id=n.entity_id, label=n.label, node_type=n.node_type, attrs=n.attrs)
        for n in nodes
    ] + extra_nodes

    out_edges = [
        GraphEdgeOut(
            id=e.id,
            from_node_id=e.from_node_id,
            to_node_id=e.to_node_id,
            type=e.type,
            weight=e.weight,
            edge_strength=e.edge_strength,
            verification_method=e.verification_method,
            verification_confidence=e.verification_confidence,
            attrs=e.attrs,
        )
        for e in unique_edges
    ] + extra_edges

    return NeighborhoodResponse(
        center_node_id=center_node.id,  # GraphNode PK — matches n.id in frontend
        nodes=out_nodes,
        edges=out_edges,
        depth=depth,
        truncated=truncated,
        diagnostics=diagnostics,
        virtual_center_node=virtual_center_node,
        co_participants=co_participants,
    )


async def get_case_graph(
    session: AsyncSession,
    case_id: uuid.UUID,
    depth: int = 1,
    limit: int = 300,
    focus_signal_id: uuid.UUID | None = None,
) -> Optional[CaseGraphResponse]:
    """Build a graph from all entities referenced by a case's signals.

    Collects seed entity IDs from every signal in the case, finds
    corresponding GraphNodes, then runs a unified BFS expansion
    (same algorithm as get_graph_neighborhood but with multiple seeds).
    """
    case = await get_case_by_id(session, case_id)
    if case is None:
        return None

    # Collect all entity_ids from signals and build signal briefs
    raw_seed_ids: list[uuid.UUID] = []
    seen_raw_ids: set[uuid.UUID] = set()
    signal_briefs: list[CaseSignalBrief] = []
    focus_signal: RiskSignal | None = None

    for item in case.items:
        sig = item.signal
        eids = [uuid.UUID(eid) for eid in sig.entity_ids]
        if focus_signal_id is not None and sig.id == focus_signal_id:
            focus_signal = sig
        for eid in eids:
            if eid not in seen_raw_ids:
                seen_raw_ids.add(eid)
                raw_seed_ids.append(eid)

    # Expand seeds to include cluster siblings (single batched query)
    resolved_seed_set = await resolve_entity_ids_with_clusters(session, raw_seed_ids)
    seen_entity_ids: set[uuid.UUID] = set()
    seed_entity_ids: list[uuid.UUID] = []
    for eid in raw_seed_ids:
        if eid not in seen_entity_ids:
            seen_entity_ids.add(eid)
            seed_entity_ids.append(eid)
    for eid in resolved_seed_set:
        if eid not in seen_entity_ids:
            seen_entity_ids.add(eid)
            seed_entity_ids.append(eid)
        signal_briefs.append(
            CaseSignalBrief(
                id=sig.id,
                typology_code=sig.typology.code,
                typology_name=sig.typology.name,
                severity=sig.severity,
                confidence=sig.data_completeness,
                title=sig.title,
                summary=sig.summary,
                entity_ids=eids,
            )
        )

    if not seed_entity_ids:
        return CaseGraphResponse(
            case_id=case.id,
            case_title=case.title,
            case_severity=case.severity,
            case_status=case.status,
            seed_entity_ids=[],
            nodes=[],
            edges=[],
            signals=signal_briefs,
            truncated=False,
            focus_signal_summary=(
                CaseFocusSignalSummary(
                    id=focus_signal.id,
                    typology_code=focus_signal.typology.code,
                    typology_name=focus_signal.typology.name,
                    severity=focus_signal.severity,
                    confidence=focus_signal.data_completeness,
                    title=focus_signal.title,
                    summary=focus_signal.summary,
                    period_start=focus_signal.period_start,
                    period_end=focus_signal.period_end,
                    pattern_label=focus_signal.typology.name,
                )
                if focus_signal is not None
                else None
            ),
            focus_entity_ids=[uuid.UUID(eid) for eid in focus_signal.entity_ids]
            if focus_signal is not None
            else [],
            focus_edge_ids=[],
        )

    # Find seed GraphNodes by entity_id
    seed_stmt = select(GraphNode).where(GraphNode.entity_id.in_(seed_entity_ids))
    seed_result = await session.execute(seed_stmt)
    seed_nodes = list(seed_result.scalars().all())

    # If some seed entities lack GraphNodes, create virtual nodes from Entity table
    found_entity_ids = {n.entity_id for n in seed_nodes}
    missing_entity_ids = [eid for eid in seed_entity_ids if eid not in found_entity_ids]
    virtual_nodes: list[GraphNodeOut] = []

    if missing_entity_ids:
        entity_stmt = select(Entity).where(Entity.id.in_(missing_entity_ids))
        entity_result = await session.execute(entity_stmt)
        for entity in entity_result.scalars().all():
            virtual_nodes.append(
                GraphNodeOut(
                    id=entity.id,  # Use entity ID as node ID for virtual nodes
                    entity_id=entity.id,
                    label=entity.name,
                    node_type=entity.type,
                    attrs={
                        "virtual": True,
                        "identifiers": entity.identifiers or {},
                    },
                )
            )

    if not seed_nodes and not virtual_nodes:
        return CaseGraphResponse(
            case_id=case.id,
            case_title=case.title,
            case_severity=case.severity,
            case_status=case.status,
            seed_entity_ids=seed_entity_ids,
            nodes=[],
            edges=[],
            signals=signal_briefs,
            truncated=False,
            er_pending=True,
            focus_signal_summary=(
                CaseFocusSignalSummary(
                    id=focus_signal.id,
                    typology_code=focus_signal.typology.code,
                    typology_name=focus_signal.typology.name,
                    severity=focus_signal.severity,
                    confidence=focus_signal.data_completeness,
                    title=focus_signal.title,
                    summary=focus_signal.summary,
                    period_start=focus_signal.period_start,
                    period_end=focus_signal.period_end,
                    pattern_label=focus_signal.typology.name,
                )
                if focus_signal is not None
                else None
            ),
            focus_entity_ids=[uuid.UUID(eid) for eid in focus_signal.entity_ids]
            if focus_signal is not None
            else [],
            focus_edge_ids=[],
        )

    # BFS from all seed nodes simultaneously
    visited_node_ids: set[uuid.UUID] = {n.id for n in seed_nodes}
    frontier: set[uuid.UUID] = set(visited_node_ids)
    all_edges: list[GraphEdge] = []

    if depth == 0:
        # Seed-only mode: only edges where BOTH endpoints are seed nodes
        if visited_node_ids:
            edge_stmt = select(GraphEdge).where(
                GraphEdge.from_node_id.in_(visited_node_ids),
                GraphEdge.to_node_id.in_(visited_node_ids),
            )
            edge_result = await session.execute(edge_stmt)
            all_edges = list(edge_result.scalars().all())
    else:
        for _ in range(depth):
            if not frontier:
                break

            edge_stmt = select(GraphEdge).where(
                (GraphEdge.from_node_id.in_(frontier))
                | (GraphEdge.to_node_id.in_(frontier))
            )
            edge_result = await session.execute(edge_stmt)
            edges = list(edge_result.scalars().all())
            all_edges.extend(edges)

            new_frontier: set[uuid.UUID] = set()
            for e in edges:
                if e.from_node_id not in visited_node_ids:
                    new_frontier.add(e.from_node_id)
                if e.to_node_id not in visited_node_ids:
                    new_frontier.add(e.to_node_id)

            visited_node_ids |= new_frontier
            frontier = new_frontier

            if len(visited_node_ids) >= limit:
                break

    truncated = len(visited_node_ids) >= limit

    # Load all visited nodes
    node_stmt = select(GraphNode).where(GraphNode.id.in_(visited_node_ids)).limit(limit)
    node_result = await session.execute(node_stmt)
    nodes = list(node_result.scalars().all())

    # Deduplicate edges
    seen_edges: set[uuid.UUID] = set()
    unique_edges: list[GraphEdge] = []
    for e in all_edges:
        if e.id not in seen_edges:
            seen_edges.add(e.id)
            unique_edges.append(e)

    real_nodes = [
        GraphNodeOut(
            id=n.id,
            entity_id=n.entity_id,
            label=n.label,
            node_type=n.node_type,
            attrs=n.attrs,
        )
        for n in nodes
    ]

    # Merge virtual nodes (for entities without GraphNode entries)
    real_entity_ids = {n.entity_id for n in real_nodes}
    for vn in virtual_nodes:
        if vn.entity_id not in real_entity_ids:
            real_nodes.append(vn)

    er_pending = len(virtual_nodes) > 0
    focus_entity_set = (
        set(_to_uuid_list(focus_signal.entity_ids or []))
        if focus_signal is not None
        else set()
    )
    node_to_entity = {node.id: node.entity_id for node in real_nodes}
    focus_edge_ids: list[uuid.UUID] = []
    if focus_entity_set:
        for edge in unique_edges:
            from_entity = node_to_entity.get(edge.from_node_id)
            to_entity = node_to_entity.get(edge.to_node_id)
            if from_entity in focus_entity_set or to_entity in focus_entity_set:
                focus_edge_ids.append(edge.id)

    return CaseGraphResponse(
        case_id=case.id,
        case_title=case.title,
        case_severity=case.severity,
        case_status=case.status,
        seed_entity_ids=seed_entity_ids,
        nodes=real_nodes,
        edges=[
            GraphEdgeOut(
                id=e.id,
                from_node_id=e.from_node_id,
                to_node_id=e.to_node_id,
                type=e.type,
                weight=e.weight,
                edge_strength=e.edge_strength,
                verification_method=e.verification_method,
                verification_confidence=e.verification_confidence,
                attrs=e.attrs,
            )
            for e in unique_edges
        ],
        signals=signal_briefs,
        truncated=truncated,
        er_pending=er_pending,
        focus_signal_summary=(
            CaseFocusSignalSummary(
                id=focus_signal.id,
                typology_code=focus_signal.typology.code,
                typology_name=focus_signal.typology.name,
                severity=focus_signal.severity,
                confidence=focus_signal.data_completeness,
                title=focus_signal.title,
                summary=focus_signal.summary,
                period_start=focus_signal.period_start,
                period_end=focus_signal.period_end,
                pattern_label=focus_signal.typology.name,
            )
            if focus_signal is not None
            else None
        ),
        focus_entity_ids=sorted(focus_entity_set, key=lambda eid: str(eid)),
        focus_edge_ids=focus_edge_ids,
    )


# --- Analytical coverage ---


async def get_analytical_coverage(session: AsyncSession) -> list[dict]:
    """Build analytical coverage: per-typology execution status.

    For each registered typology, shows:
    - required_domains
    - domains_available (which of the required domains have recent data)
    - apt (all required domains available)
    - signals_30d (count of signals produced in last 30 days)
    - last_signal_at (most recent signal creation)
    """
    from shared.typologies.registry import get_all_typologies

    now = datetime.now(timezone.utc)
    window_30d = now - timedelta(days=30)

    # Get available event types (domains) — no time restriction so bulk connectors
    # (empresa, remuneracao) that are ingested once are not incorrectly marked as missing.
    domain_stmt = select(Event.type).distinct()
    domain_result = await session.execute(domain_stmt)
    available_domains = {row.type for row in domain_result}

    # Get signal counts per typology in last 30 days
    signal_stmt = (
        select(
            Typology.code,
            func.count().label("cnt"),
            func.max(RiskSignal.created_at).label("last_at"),
        )
        .join(Typology)
        .where(RiskSignal.created_at >= window_30d)
        .group_by(Typology.code)
    )
    signal_result = await session.execute(signal_stmt)
    signal_map: dict[str, tuple[int, datetime | None]] = {}
    for row in signal_result:
        signal_map[row.code] = (row.cnt, row.last_at)

    # Get most recent run per typology from TypologyRunLog
    latest_run_sub = (
        select(
            TypologyRunLog.typology_code,
            func.max(TypologyRunLog.started_at).label("max_started"),
        )
        .group_by(TypologyRunLog.typology_code)
        .subquery()
    )
    run_stmt = (
        select(TypologyRunLog)
        .join(
            latest_run_sub,
            (TypologyRunLog.typology_code == latest_run_sub.c.typology_code)
            & (TypologyRunLog.started_at == latest_run_sub.c.max_started),
        )
    )
    run_result = await session.execute(run_stmt)
    run_map: dict[str, TypologyRunLog] = {}
    for row in run_result.scalars():
        run_map[row.typology_code] = row

    # Get last successful run per typology
    latest_success_sub = (
        select(
            TypologyRunLog.typology_code,
            func.max(TypologyRunLog.started_at).label("max_started"),
        )
        .where(TypologyRunLog.status == "success")
        .group_by(TypologyRunLog.typology_code)
        .subquery()
    )
    success_stmt = (
        select(TypologyRunLog.typology_code, latest_success_sub.c.max_started)
        .join(
            latest_success_sub,
            TypologyRunLog.typology_code == latest_success_sub.c.typology_code,
        )
    )
    success_result = await session.execute(success_stmt)
    success_map: dict[str, datetime] = {}
    for row in success_result:
        success_map[row.typology_code] = row.max_started

    # Build coverage for each typology
    items: list[dict] = []
    for typo in get_all_typologies():
        required = typo.required_domains
        available = [d for d in required if d in available_domains]
        missing = [d for d in required if d not in available_domains]
        apt = len(missing) == 0
        sig_count, last_at = signal_map.get(typo.id, (0, None))

        from shared.typologies.factor_metadata import TYPOLOGY_LEGAL_METADATA
        legal_meta = TYPOLOGY_LEGAL_METADATA.get(typo.id, {})

        last_run = run_map.get(typo.id)
        item = {
            "typology_code": typo.id,
            "typology_name": typo.name,
            "required_domains": required,
            "domains_available": available,
            "domains_missing": missing,
            "apt": apt,
            "signals_30d": sig_count,
            "last_signal_at": last_at,
            "last_run_at": last_run.started_at if last_run else None,
            "last_run_status": last_run.status if last_run else None,
            "last_run_candidates": last_run.candidates if last_run else None,
            "last_run_signals_created": last_run.signals_created if last_run else None,
            "last_run_signals_deduped": last_run.signals_deduped if last_run else None,
            "last_run_signals_blocked": last_run.signals_blocked if last_run else None,
            "last_run_error_message": last_run.error_message[:200] if last_run and last_run.error_message else None,
            "last_success_at": success_map.get(typo.id),
            "corruption_types": legal_meta.get("corruption_types", []),
            "spheres": legal_meta.get("spheres", []),
            "evidence_level": legal_meta.get("evidence_level", "indirect"),
            "description_legal": legal_meta.get("description_legal"),
        }
        items.append(item)

    return items


# --- Org summary ---


async def get_org_summary(
    session: AsyncSession,
    entity_id: uuid.UUID,
) -> Optional[dict]:
    """Get organization summary with aggregated stats."""
    entity = await get_entity_by_id(session, entity_id)
    if entity is None:
        return None

    # Count events where entity is a participant
    event_count_stmt = (
        select(func.count())
        .select_from(EventParticipant)
        .where(EventParticipant.entity_id == entity_id)
    )
    event_count = (await session.execute(event_count_stmt)).scalar_one()

    # Get signals involving this entity (including cluster siblings)
    resolved_ids = await resolve_entity_ids_with_clusters(session, [entity_id])
    signal_stmt = (
        select(RiskSignal)
        .options(selectinload(RiskSignal.typology))
        .order_by(RiskSignal.created_at.desc())
        .limit(50)
    )
    signal_result = await session.execute(signal_stmt)
    all_signals = signal_result.scalars().all()

    # Filter signals that reference this entity or any cluster sibling
    entity_signals = [
        s for s in all_signals
        if resolved_ids.intersection(
            uuid.UUID(str(eid)) for eid in (s.entity_ids or [])
        )
    ]

    severity_counts: dict[str, int] = {}
    for s in entity_signals:
        severity_counts[s.severity] = severity_counts.get(s.severity, 0) + 1

    return {
        "id": entity.id,
        "name": entity.name,
        "type": entity.type,
        "identifiers": entity.identifiers,
        "attrs": entity.attrs,
        "event_count": event_count,
        "signal_count": len(entity_signals),
        "severity_distribution": severity_counts,
        "signals": [
            {
                "id": s.id,
                "typology_code": s.typology.code,
                "severity": s.severity,
                "title": s.title,
                "created_at": s.created_at,
            }
            for s in entity_signals[:10]
        ],
    }


# ---------------------------------------------------------------------------
# Embedding / pgvector helpers
# ---------------------------------------------------------------------------

def get_entity_embeddings_for_er(session, entity_ids: list) -> dict:
    """Load text embeddings for entities, keyed by str(entity_id).

    Returns dict mapping source_id -> list[float] embedding vector.
    Used by the ER semantic matching pass. Sync-compatible.
    """
    from sqlalchemy import text

    if not entity_ids:
        return {}

    id_strs = [str(eid) for eid in entity_ids]
    sql = text("""
        SELECT tc.source_id, te.embedding::text
        FROM text_embedding te
        JOIN text_corpus tc ON tc.id = te.corpus_id
        WHERE tc.source_type = 'entity'
          AND tc.source_id = ANY(:source_ids)
    """)
    rows = session.execute(sql, {"source_ids": id_strs}).fetchall()
    result: dict = {}
    for source_id, embedding_text in rows:
        vec = [float(v) for v in embedding_text.strip("[]").split(",")]
        result[source_id] = vec
    return result


def find_similar_signal_embeddings(
    session,
    embedding_vector: list,
    threshold: float = 0.90,
    limit: int = 5,
) -> list:
    """Find signals with cosine similarity >= threshold using pgvector.

    Returns list of dicts with source_id and similarity score.
    Used for semantic signal deduplication. Sync-compatible.
    """
    from sqlalchemy import text

    vec_str = "[" + ",".join(str(v) for v in embedding_vector) + "]"
    sql = text("""
        SELECT
            tc.source_id,
            1 - (te.embedding <=> :query_vec::vector) AS similarity
        FROM text_embedding te
        JOIN text_corpus tc ON tc.id = te.corpus_id
        WHERE tc.source_type = 'signal'
          AND 1 - (te.embedding <=> :query_vec::vector) >= :threshold
        ORDER BY te.embedding <=> :query_vec::vector
        LIMIT :limit
    """)
    rows = session.execute(
        sql, {"query_vec": vec_str, "threshold": threshold, "limit": limit}
    ).fetchall()
    return [{"source_id": row.source_id, "similarity": float(row.similarity)} for row in rows]


async def get_public_sources(session: AsyncSession) -> dict:
    """Build public sources response with veracity metadata.

    Queries CoverageRegistry and enriches with static veracity profiles
    and domain guard configuration.
    """
    from datetime import datetime as dt, timezone as tz

    from shared.connectors import ConnectorRegistry
    from shared.connectors.domain_guard import (
        DOMAIN_EXCEPTIONS,
        GOVERNMENT_TLDS,
        is_government_domain,
    )
    from shared.connectors.veracity import SOURCE_VERACITY_REGISTRY

    # Base URLs per connector (static mapping)
    _CONNECTOR_URLS: dict[str, str] = {
        "portal_transparencia": "https://api.portaldatransparencia.gov.br",
        "compras_gov": "https://compras.dados.gov.br",
        "comprasnet_contratos": "https://compras.dados.gov.br",
        "pncp": "https://pncp.gov.br",
        "transferegov": "https://api.transferegov.gestao.gov.br",
        "camara": "https://dadosabertos.camara.leg.br",
        "senado": "https://legis.senado.leg.br",
        "tse": "https://dadosabertos.tse.jus.br",
        "receita_cnpj": "https://dados.rfb.gov.br",
        "querido_diario": "https://api.queridodiario.ok.org.br",
    }

    # Get all coverage rows
    stmt = select(CoverageRegistry)
    rows = (await session.execute(stmt)).scalars().all()
    cov_map = {(r.connector, r.job): r for r in rows}

    items = []
    for name, cls in ConnectorRegistry.items():
        connector = cls()
        base_url = _CONNECTOR_URLS.get(name, "")
        for job in connector.list_jobs():
            key = f"{name}:{job.name}"
            profile = SOURCE_VERACITY_REGISTRY.get(key)
            cov = cov_map.get((name, job.name))

            veracity_detail = None
            if profile:
                veracity_detail = {
                    "government_domain": profile.government_domain,
                    "legal_authority": profile.legal_authority,
                    "public_availability": profile.public_availability,
                    "official_api_documented": profile.official_api_documented,
                    "metadata_traceability": profile.metadata_traceability,
                    "composite_score": profile.composite_score,
                    "label": profile.veracity_label,
                }

            items.append({
                "connector": name,
                "job": job.name,
                "domain": job.domain,
                "base_url": base_url,
                "is_government": is_government_domain(base_url) if base_url else False,
                "veracity": veracity_detail,
                "status": cov.status if cov else "pending",
                "freshness_lag_hours": cov.freshness_lag_hours if cov else None,
                "total_items": cov.total_items if cov else 0,
                "compliance_status": cov.compliance_status if cov else None,
            })

    exceptions = [
        {
            "domain": exc.domain,
            "justification": exc.justification,
            "max_veracity": exc.max_veracity,
            "review_by": exc.review_by.isoformat(),
        }
        for exc in DOMAIN_EXCEPTIONS.values()
    ]

    return {
        "items": items,
        "total": len(items),
        "policy_version": "1.0",
        "domain_whitelist": sorted(GOVERNMENT_TLDS),
        "controlled_exceptions": exceptions,
        "generated_at": dt.now(tz.utc),
    }


async def get_cross_source_overlap(session: AsyncSession) -> list[dict]:
    """Returns how many entities appear in exactly N distinct connectors."""
    from sqlalchemy import text

    result = await session.execute(
        text("""
            SELECT source_count, COUNT(*) AS entity_count
            FROM (
                SELECT ers.entity_id, COUNT(DISTINCT rs.connector) AS source_count
                FROM entity_raw_source ers
                JOIN raw_source rs ON rs.id = ers.raw_source_id
                GROUP BY ers.entity_id
            ) sub
            GROUP BY source_count
            ORDER BY source_count
        """)
    )
    return [{"source_count": r[0], "entity_count": r[1]} for r in result.fetchall()]


async def get_data_quality_dashboard(session: AsyncSession) -> dict:
    """Aggregate data-quality metrics: coverage registry, cross-source overlap, and drop alerts."""
    from datetime import timezone as _tz
    from sqlalchemy import text as _text

    now = datetime.now(tz=_tz.utc)
    cutoff = now - timedelta(days=7)

    # Current coverage entries
    cov_rows = (await session.execute(select(CoverageRegistry))).scalars().all()

    sources = [
        {
            "connector": row.connector,
            "job": row.job,
            "total_items": row.total_items,
            "freshness_lag_hours": row.freshness_lag_hours,
            "last_success_at": row.last_success_at.isoformat() if row.last_success_at else None,
            "veracity_score": row.veracity_score,
            "status": row.status,
        }
        for row in cov_rows
    ]

    current_by_key: dict[tuple[str, str], int] = {
        (row.connector, row.job): row.total_items for row in cov_rows
    }

    # Compare against BaselineSnapshot for 7+ day old coverage data
    baseline_result = await session.execute(
        _text("""
            SELECT scope_key, (metrics->>'total_items')::bigint AS total_items
            FROM baseline_snapshot
            WHERE baseline_type = 'coverage_registry'
              AND window_end <= :cutoff
            ORDER BY window_end DESC
        """),
        {"cutoff": cutoff},
    )
    prior_by_key: dict[tuple[str, str], int] = {}
    for brow in baseline_result.fetchall():
        parts = str(brow[0]).split(":", 1)
        if len(parts) == 2:
            key = (parts[0], parts[1])
            if key not in prior_by_key:
                prior_by_key[key] = int(brow[1])

    alerts: list[dict] = []
    for (connector, job), current_total in current_by_key.items():
        prior_total = prior_by_key.get((connector, job))
        if prior_total is not None and prior_total > 0:
            drop_pct = (prior_total - current_total) / prior_total * 100.0
            if drop_pct > 20.0:
                alerts.append(
                    {
                        "connector": connector,
                        "job": job,
                        "alert": "weekly_drop",
                        "drop_pct": round(drop_pct, 2),
                    }
                )

    cross_source_overlap = await get_cross_source_overlap(session)

    return {
        "sources": sources,
        "cross_source_overlap": cross_source_overlap,
        "alerts": alerts,
    }


async def search_entities(
    session: AsyncSession,
    q: str,
    entity_type: str | None = None,
    limit: int = 20,
) -> list[dict]:
    """
    Fuzzy entity search using pg_trgm similarity on name_normalized.

    Person results are scoped to public servants only (portal_transparencia /
    pt_servidores_remuneracao) via a join through entity_raw_source → raw_source.
    CPF from public government sources (LAI 12.527/2011) is returned for auditor use.
    """
    from sqlalchemy import text

    if entity_type == "person":
        # Persons: only return public servants to comply with LGPD
        sql = text("""
            SELECT DISTINCT e.id, e.name, e.name_normalized, e.type,
                   e.identifiers->>'cnpj' AS cnpj,
                   e.identifiers->>'cpf' AS cpf,
                   e.cluster_id,
                   similarity(e.name_normalized, :q) AS score,
                   e.cluster_confidence
            FROM entity e
            JOIN entity_raw_source ers ON ers.entity_id = e.id
            JOIN raw_source rs ON rs.id = ers.raw_source_id
                AND rs.connector = 'portal_transparencia'
                AND rs.job = 'pt_servidores_remuneracao'
            WHERE e.name_normalized % :q
              AND e.type = 'person'
            ORDER BY score DESC
            LIMIT :limit
        """)
        result = await session.execute(sql, {"q": q, "limit": limit})
    else:
        type_filter = "AND e.type = :type" if entity_type is not None else ""
        sql = text(f"""
            SELECT e.id, e.name, e.name_normalized, e.type,
                   e.identifiers->>'cnpj' AS cnpj,
                   e.identifiers->>'cpf' AS cpf,
                   e.cluster_id,
                   similarity(e.name_normalized, :q) AS score,
                   e.cluster_confidence
            FROM entity e
            WHERE e.name_normalized % :q
              {type_filter}
            ORDER BY score DESC
            LIMIT :limit
        """)
        params: dict = {"q": q, "limit": limit}
        if entity_type is not None:
            params["type"] = entity_type
        result = await session.execute(sql, params)

    rows = result.fetchall()
    return [
        {
            "entity_id": str(r[0]),
            "name": r[1],
            "name_normalized": r[2],
            "type": r[3],
            "cnpj": r[4],
            "cpf": r[5],
            "cluster_id": str(r[6]) if r[6] else None,
            "score": float(r[7]),
            "cluster_confidence": r[8],
        }
        for r in rows
    ]

async def get_entity_path(
    session: AsyncSession,
    from_entity_id: uuid.UUID,
    to_entity_id: uuid.UUID,
    max_hops: int = 5,
) -> EntityPathResponse:
    """Find shortest path between two entities using recursive CTE over graph_node/graph_edge.

    Temporal bounds (first_seen_at/last_seen_at) are computed via EventParticipant -> Event.
    Returns EntityPathResponse with found=False if no path exists within max_hops.
    """
    from sqlalchemy import text

    # Recursive CTE: traverse graph_edge via graph_node.entity_id linkage.
    # graph_edge stores from_node_id/to_node_id as graph_node.id (UUID PK),
    # so we join graph_node to map entity_id <-> node id at each hop.
    path_sql = text("""
        WITH RECURSIVE path_search AS (
            SELECT
                gn_from.entity_id   AS src_entity_id,
                gn_to.entity_id     AS tgt_entity_id,
                ge.type             AS edge_type,
                ARRAY[gn_from.entity_id::text]              AS visited,
                ARRAY[ge.id::text]                          AS edge_ids,
                ARRAY[gn_from.entity_id::text,
                      gn_to.entity_id::text]                AS node_path,
                1                                           AS depth
            FROM graph_edge ge
            JOIN graph_node gn_from ON gn_from.id = ge.from_node_id
            JOIN graph_node gn_to   ON gn_to.id   = ge.to_node_id
            WHERE gn_from.entity_id = :from_id
              AND gn_to.entity_id  != :from_id

            UNION ALL

            SELECT
                ps.src_entity_id,
                gn_to.entity_id     AS tgt_entity_id,
                ge.type             AS edge_type,
                ps.visited || gn_from.entity_id::text,
                ps.edge_ids || ge.id::text,
                ps.node_path || gn_to.entity_id::text,
                ps.depth + 1
            FROM path_search ps
            JOIN graph_node gn_from ON gn_from.entity_id = ps.tgt_entity_id
            JOIN graph_edge ge      ON ge.from_node_id   = gn_from.id
            JOIN graph_node gn_to   ON gn_to.id          = ge.to_node_id
            WHERE ps.depth < :max_hops
              AND NOT (gn_from.entity_id::text = ANY(ps.visited))
              AND NOT (gn_to.entity_id::text   = ANY(ps.visited))
        )
        SELECT src_entity_id, tgt_entity_id, edge_type, visited, edge_ids, node_path, depth
        FROM path_search
        WHERE tgt_entity_id = :to_id
        ORDER BY depth ASC
        LIMIT 1
    """)

    result = await session.execute(
        path_sql,
        {"from_id": str(from_entity_id), "to_id": str(to_entity_id), "max_hops": max_hops},
    )
    row = result.fetchone()
    if row is None:
        return EntityPathResponse(found=False, hops=None, path=[])

    node_path: list[str] = list(row.node_path)
    edge_ids: list[str] = list(row.edge_ids)
    depth: int = int(row.depth)

    # Fetch node labels for all entity UUIDs in path
    node_uuids = [uuid.UUID(eid) for eid in node_path]
    label_stmt = select(GraphNode.entity_id, GraphNode.label, GraphNode.node_type).where(
        GraphNode.entity_id.in_(node_uuids)
    )
    label_rows = (await session.execute(label_stmt)).all()
    label_map: dict[uuid.UUID, tuple[str, str]] = {
        r.entity_id: (r.label, r.node_type) for r in label_rows
    }

    # Fetch edges to get their types (preserving order via edge_ids)
    edge_uuids = [uuid.UUID(eid) for eid in edge_ids]
    edge_stmt = select(GraphEdge.id, GraphEdge.type).where(GraphEdge.id.in_(edge_uuids))
    edge_rows = (await session.execute(edge_stmt)).all()
    edge_type_map: dict[uuid.UUID, str] = {r.id: r.type for r in edge_rows}

    # Compute temporal bounds per hop via EventParticipant -> Event
    hops: list[PathHopOut] = []
    for i in range(depth):
        from_eid = uuid.UUID(node_path[i])
        to_eid = uuid.UUID(node_path[i + 1])
        edge_id = uuid.UUID(edge_ids[i])

        from_label, _ = label_map.get(from_eid, ("unknown", "unknown"))
        to_label, _ = label_map.get(to_eid, ("unknown", "unknown"))
        edge_type = edge_type_map.get(edge_id, "unknown")

        # Temporal bounds: events where both entities co-participated
        temporal_sql = text("""
            SELECT
                MIN(e.occurred_at) AS first_seen_at,
                MAX(e.occurred_at) AS last_seen_at
            FROM event e
            JOIN event_participant ep1 ON ep1.event_id = e.id AND ep1.entity_id = :from_eid
            JOIN event_participant ep2 ON ep2.event_id = e.id AND ep2.entity_id = :to_eid
            WHERE e.occurred_at IS NOT NULL
        """)
        t_result = await session.execute(
            temporal_sql, {"from_eid": str(from_eid), "to_eid": str(to_eid)}
        )
        t_row = t_result.fetchone()
        first_seen_at = t_row.first_seen_at if t_row else None
        last_seen_at = t_row.last_seen_at if t_row else None

        hops.append(
            PathHopOut(
                from_entity_id=from_eid,
                to_entity_id=to_eid,
                from_label=from_label,
                to_label=to_label,
                edge_type=edge_type,
                first_seen_at=first_seen_at,
                last_seen_at=last_seen_at,
            )
        )

    return EntityPathResponse(found=True, hops=depth, path=hops)


async def get_dossier_timeline(
    session: AsyncSession,
    case_id: uuid.UUID,
) -> dict | None:
    """Full timeline data for a case dossier: events with participants, signals, entities, legal hypotheses."""
    from shared.models.orm import LegalViolationHypothesis
    from shared.typologies.factor_metadata import get_factor_descriptions
    from shared.utils.query import execute_chunked_in

    # 1. Fetch case
    case_stmt = select(Case).where(Case.id == case_id)
    case = (await session.execute(case_stmt)).scalar_one_or_none()
    if case is None:
        return None

    # 2. Fetch all signals for this case with typology info
    signals_stmt = (
        select(
            RiskSignal.id,
            RiskSignal.typology_id,
            RiskSignal.severity,
            RiskSignal.data_completeness,
            RiskSignal.title,
            RiskSignal.summary,
            RiskSignal.period_start,
            RiskSignal.period_end,
            RiskSignal.entity_ids,
            RiskSignal.event_ids,
            RiskSignal.factors,
            Typology.code.label("typology_code"),
            Typology.name.label("typology_name"),
        )
        .join(CaseItem, CaseItem.signal_id == RiskSignal.id)
        .join(Typology, RiskSignal.typology_id == Typology.id)
        .where(CaseItem.case_id == case_id)
        .order_by(RiskSignal.data_completeness.desc())
    )
    sig_rows = (await session.execute(signals_stmt)).all()

    # 3. Collect all event_ids and entity_ids from signals
    all_event_ids_str: set[str] = set()
    all_entity_ids_str: set[str] = set()
    for r in sig_rows:
        for eid in r.event_ids or []:
            all_event_ids_str.add(str(eid))
        for eid in r.entity_ids or []:
            all_entity_ids_str.add(str(eid))

    all_event_uuids = _to_uuid_list(list(all_event_ids_str))
    all_entity_uuids = _to_uuid_list(list(all_entity_ids_str))

    # 4. Fetch events with attrs
    events_list = await execute_chunked_in(
        session,
        lambda batch: select(Event).where(Event.id.in_(batch)),
        all_event_uuids,
    )
    events_by_id: dict[uuid.UUID, Any] = {e.id: e for e in events_list}

    # 5. Fetch participants for all events
    participants_list = await execute_chunked_in(
        session,
        lambda batch: select(EventParticipant).where(EventParticipant.event_id.in_(batch)),
        all_event_uuids,
    )
    participants_by_event: dict[uuid.UUID, list] = defaultdict(list)
    for p in participants_list:
        participants_by_event[p.event_id].append(p)
        all_entity_ids_str.add(str(p.entity_id))

    # Re-collect entity UUIDs (participants may reference entities not in signal.entity_ids)
    all_entity_uuids = _to_uuid_list(list(all_entity_ids_str))

    # 6. Fetch all entities (full identifiers, NO masking)
    entities_list = await execute_chunked_in(
        session,
        lambda batch: select(Entity).where(Entity.id.in_(batch)),
        all_entity_uuids,
    )
    entities_by_id: dict[uuid.UUID, Any] = {e.id: e for e in entities_list}

    # 7. Build signal-to-event index (which signals reference which events)
    signal_events_map: dict[uuid.UUID, list[str]] = defaultdict(list)
    for r in sig_rows:
        for eid_str in r.event_ids or []:
            try:
                signal_events_map[uuid.UUID(str(eid_str))].append(str(r.id))
            except (ValueError, TypeError):
                continue

    # 8. Build signals output
    signals_out = []
    for r in sig_rows:
        factor_descs = get_factor_descriptions(
            r.factors or {},
            typology_code=r.typology_code,
        )
        signals_out.append({
            "id": str(r.id),
            "typology_code": r.typology_code,
            "typology_name": r.typology_name,
            "severity": r.severity,
            "title": r.title,
            "summary": r.summary,
            "data_completeness": r.data_completeness,
            "factors": r.factors or {},
            "factor_descriptions": factor_descs,
            "period_start": r.period_start.isoformat() if r.period_start else None,
            "period_end": r.period_end.isoformat() if r.period_end else None,
            "entity_count": len(r.entity_ids or []),
            "event_count": len(r.event_ids or []),
        })

    # 9. Build events output (with participants and linked signals)
    events_out = []
    for eid in all_event_uuids:
        ev = events_by_id.get(eid)
        if ev is None:
            continue
        ev_participants = participants_by_event.get(eid, [])
        ev_signal_ids = signal_events_map.get(eid, [])

        # Build signal snippets for this event
        ev_signals = []
        for sid_str in ev_signal_ids:
            for r in sig_rows:
                if str(r.id) == sid_str:
                    ev_signals.append({
                        "id": str(r.id),
                        "typology_code": r.typology_code,
                        "typology_name": r.typology_name,
                        "severity": r.severity,
                        "title": r.title,
                        "factors": r.factors or {},
                        "period_start": r.period_start.isoformat() if r.period_start else None,
                        "period_end": r.period_end.isoformat() if r.period_end else None,
                        "data_completeness": r.data_completeness,
                    })
                    break

        events_out.append({
            "id": str(ev.id),
            "type": ev.type,
            "occurred_at": ev.occurred_at.isoformat() if ev.occurred_at else None,
            "description": ev.description,
            "value_brl": ev.value_brl,
            "source_connector": ev.source_connector,
            "attrs": ev.attrs or {},
            "participants": [
                {
                    "entity_id": str(p.entity_id),
                    "role": p.role,
                    "role_label": _role_label(p.role),
                }
                for p in ev_participants
            ],
            "signals": ev_signals,
        })

    # Sort events by occurred_at (nulls last)
    events_out.sort(key=lambda e: e["occurred_at"] or "9999")

    # 10. Build entities output
    entities_out = [
        {
            "id": str(e.id),
            "type": e.type,
            "name": e.name,
            "identifiers": e.identifiers or {},
            "attrs": e.attrs or {},
        }
        for e in entities_list
    ]

    # 11. Legal hypotheses
    legal_stmt = (
        select(LegalViolationHypothesis)
        .where(LegalViolationHypothesis.case_id == case_id)
        .order_by(LegalViolationHypothesis.confidence.desc())
    )
    legal_rows = (await session.execute(legal_stmt)).scalars().all()
    legal_hypotheses = [
        {
            "law": lh.law_name,
            "article": lh.article,
            "violation_type": lh.violation_type,
            "description": None,
            "signal_cluster": lh.signal_cluster or [],
            "confidence": lh.confidence,
        }
        for lh in legal_rows
    ]

    # 12. Related cases
    entity_names = list((case.attrs or {}).get("entity_names", []))
    related_cases = []
    if entity_names:
        related_stmt = text("""
            SELECT c.id, c.title, c.severity
            FROM "case" c,
            LATERAL jsonb_array_elements_text(COALESCE(c.attrs->'entity_names', '[]'::jsonb)) AS name
            WHERE c.id != :case_id
              AND name = ANY(:entity_names)
            GROUP BY c.id, c.title, c.severity
            ORDER BY c.created_at DESC
            LIMIT 5
        """)
        result = await session.execute(
            related_stmt,
            {"case_id": case_id, "entity_names": entity_names},
        )
        related_cases = [
            {
                "id": str(r.id),
                "title": r.title,
                "severity": r.severity,
            }
            for r in result.all()
        ]

    return {
        "case": {
            "id": str(case.id),
            "title": case.title,
            "severity": case.severity,
            "status": case.status,
            "summary": case.summary,
            "case_type": case.case_type,
            "attrs": case.attrs or {},
        },
        "entities": entities_out,
        "events": events_out,
        "signals": signals_out,
        "legal_hypotheses": legal_hypotheses,
        "related_cases": related_cases,
    }


async def get_min_cluster_confidence(
    session: AsyncSession,
    entity_ids: list,
) -> int | None:
    """Return the minimum cluster_confidence across the given entity IDs.

    Returns None if no entities are found or none have a cluster_confidence set.
    This represents the weakest-link identity certainty for a signal's entity set.
    """
    if not entity_ids:
        return None
    str_ids = [str(eid) for eid in entity_ids]
    result = await session.execute(
        select(func.min(Entity.cluster_confidence)).where(
            Entity.id.in_(str_ids),
            Entity.cluster_confidence.isnot(None),
        )
    )
    return result.scalar_one_or_none()
