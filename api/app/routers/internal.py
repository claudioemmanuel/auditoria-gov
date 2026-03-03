import uuid
from datetime import datetime
import json
from typing import Any, Optional

from celery import Celery
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select

from shared.ai.classify import classify_text
from shared.ai.explain import explain_signal
from shared.config import settings
from shared.connectors import get_connector
from shared.db import async_session
from shared.db_sync import SyncSession
from shared.models.orm import IngestState, RawRun, RawSource, ReferenceData
from shared.repo.queries import get_signal_quality_metrics, replay_signal
from shared.utils.sync_async import run_async

router = APIRouter()

celery_app = Celery(broker=settings.CELERY_BROKER_URL, backend=settings.CELERY_RESULT_BACKEND)


class ExplainRequest(BaseModel):
    typology_code: str
    typology_name: str
    severity: str
    confidence: float
    title: str
    factors: dict
    evidence_refs: list[dict]


class ExplainResponse(BaseModel):
    explanation_md: str


class ClassifyRequest(BaseModel):
    text: str
    categories: list[str]


class ClassifyResponse(BaseModel):
    category: str


class RunFieldProfile(BaseModel):
    key: str
    present_count: int
    coverage_pct: float
    detected_types: list[str]
    examples: list[Any]


class RunSampleRecord(BaseModel):
    raw_id: str
    created_at: Optional[str]
    preview: dict[str, Any]
    raw_data: dict[str, Any]


class RunDetailResponse(BaseModel):
    run: dict[str, Any]
    job: dict[str, Any]
    summary: dict[str, Any]
    field_profile: list[RunFieldProfile]
    samples: list[RunSampleRecord]


PROFILE_SAMPLE_LIMIT = 200
RECORD_SAMPLE_LIMIT = 12
MAX_RAW_DATA_CHARS = 2400
MAX_PREVIEW_VALUE_CHARS = 160

PREFERRED_PREVIEW_KEYS = (
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


def _safe_iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt else None


def _value_type(value: Any) -> str:
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


def _preview_value(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return _compact_nested(value)

    if isinstance(value, str):
        return value if len(value) <= MAX_PREVIEW_VALUE_CHARS else f"{value[:MAX_PREVIEW_VALUE_CHARS]}..."

    if isinstance(value, (int, float, bool)) or value is None:
        return value

    text = json.dumps(value, ensure_ascii=False, default=str)
    return text if len(text) <= MAX_PREVIEW_VALUE_CHARS else f"{text[:MAX_PREVIEW_VALUE_CHARS]}..."


def _preview_text(value: Any) -> str:
    """Return JSON-safe preview text for nested/raw values."""
    text = json.dumps(value, ensure_ascii=False, default=str)
    return text if len(text) <= MAX_PREVIEW_VALUE_CHARS else f"{text[:MAX_PREVIEW_VALUE_CHARS]}..."


def _example_fingerprint(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    except TypeError:
        return str(value)


def _compact_nested(value: Any) -> Any:
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
        compact = {
            k: value[k]
            for k in preferred_subkeys
            if k in value
        }
        if compact:
            return compact
        keys = list(value.keys())[:4]
        return {k: value[k] for k in keys}
    if isinstance(value, list):
        first = value[0] if value else None
        return {"items": len(value), "first": _compact_nested(first)}
    if isinstance(value, str) and len(value) > MAX_PREVIEW_VALUE_CHARS:
        return f"{value[:MAX_PREVIEW_VALUE_CHARS]}..."
    return value


def _build_preview(raw_data: dict[str, Any]) -> dict[str, Any]:
    keys: list[str] = [k for k in PREFERRED_PREVIEW_KEYS if k in raw_data]
    if len(keys) < 8:
        for k in raw_data.keys():
            if k not in keys:
                keys.append(k)
            if len(keys) >= 8:
                break
    return {k: _compact_nested(raw_data.get(k)) for k in keys}


def _trim_raw_data(raw_data: dict[str, Any]) -> dict[str, Any]:
    text = str(raw_data)
    if len(text) <= MAX_RAW_DATA_CHARS:
        return raw_data
    trimmed: dict[str, Any] = {}
    for k, v in raw_data.items():
        if len(str(trimmed)) > MAX_RAW_DATA_CHARS:
            break
        trimmed[k] = _compact_nested(v)
    trimmed["_truncated"] = True
    trimmed["_note"] = "Payload reduzido para visualizacao."
    return trimmed


def _build_job_info(connector_name: str, job_name: str) -> dict[str, Any]:
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
        job_spec = next((j for j in connector.list_jobs() if j.name == job_name), None)
        if job_spec:
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
        # Keep endpoint resilient even when connector metadata is unavailable.
        pass
    return info


@router.get("/metrics")
async def task_metrics():
    """Task execution metrics — p50/p95/p99 duration per task type."""
    from shared.middleware.task_metrics import get_task_metrics
    return get_task_metrics()


@router.post("/ai/explain", response_model=ExplainResponse)
async def ai_explain(req: ExplainRequest):
    """Generate AI explanation for a risk signal."""
    explanation = await explain_signal(
        typology_code=req.typology_code,
        typology_name=req.typology_name,
        severity=req.severity,
        confidence=req.confidence,
        title=req.title,
        factors=req.factors,
        evidence_refs=req.evidence_refs,
    )
    return ExplainResponse(explanation_md=explanation)


@router.post("/ai/classify", response_model=ClassifyResponse)
async def ai_classify(req: ClassifyRequest):
    """Classify a procurement description."""
    category = await classify_text(req.text, req.categories)
    return ClassifyResponse(category=category)


# --- Ingest trigger endpoints ---


@router.post("/ingest/{connector_name}/{job_name}")
async def trigger_ingest(connector_name: str, job_name: str, cursor: Optional[str] = None):
    """Manually trigger ingestion for a specific connector job."""
    # Validate connector and job exist
    connector = get_connector(connector_name)
    job = None
    for j in connector.list_jobs():
        if j.name == job_name:
            job = j
            break
    if job is None:
        return {"status": "error", "error": f"Job '{job_name}' not found for connector '{connector_name}'"}

    result = celery_app.send_task(
        "worker.tasks.ingest_tasks.ingest_connector",
        args=[connector_name, job_name, cursor],
        queue="ingest",
    )
    return {"status": "dispatched", "task_id": result.id, "connector": connector_name, "job": job_name}


@router.post("/ingest/all")
async def trigger_ingest_all():
    """Manually trigger incremental ingestion for all connectors."""
    result = celery_app.send_task(
        "worker.tasks.ingest_tasks.ingest_all_incremental",
        queue="ingest",
    )
    return {"status": "dispatched", "task_id": result.id}


@router.get("/ingest/status")
async def ingest_status():
    """Query latest ingest state and recent runs for all connectors."""
    with SyncSession() as session:
        # Get all ingest states
        states = session.execute(
            select(IngestState).order_by(IngestState.connector, IngestState.job)
        ).scalars().all()

        # Get recent runs (enough to cover all connector:job pairs)
        recent_runs = session.execute(
            select(RawRun).order_by(RawRun.created_at.desc()).limit(200)
        ).scalars().all()

        return {
            "ingest_states": [
                {
                    "connector": s.connector,
                    "job": s.job,
                    "last_cursor": s.last_cursor,
                    "last_run_at": s.last_run_at.isoformat() if s.last_run_at else None,
                    "last_run_id": str(s.last_run_id) if s.last_run_id else None,
                }
                for s in states
            ],
            "recent_runs": [
                {
                    "id": str(r.id),
                    "connector": r.connector,
                    "job": r.job,
                    "status": r.status,
                    "items_fetched": r.items_fetched,
                    "items_normalized": r.items_normalized,
                    "started_at": r.created_at.isoformat() if r.created_at else None,
                    "finished_at": r.finished_at.isoformat() if r.finished_at else None,
                    "errors": r.errors,
                }
                for r in recent_runs
            ],
        }


@router.get("/ingest/run/{run_id}", response_model=RunDetailResponse)
async def ingest_run_detail(run_id: uuid.UUID):
    """Detailed transparency view for one ingest run with sample processed records."""
    with SyncSession() as session:
        run = session.execute(select(RawRun).where(RawRun.id == run_id)).scalar_one_or_none()
        if run is None:
            raise HTTPException(status_code=404, detail="Run not found")

        summary_row = session.execute(
            select(
                func.count(RawSource.id).label("records_stored"),
                func.count(func.distinct(RawSource.raw_id)).label("distinct_raw_ids"),
                func.min(RawSource.created_at).label("first_record_at"),
                func.max(RawSource.created_at).label("last_record_at"),
            ).where(RawSource.run_id == run_id)
        ).one()

        records_stored = int(summary_row.records_stored or 0)
        distinct_raw_ids = int(summary_row.distinct_raw_ids or 0)
        duplicate_raw_ids = max(records_stored - distinct_raw_ids, 0)

        profile_sources = (
            session.execute(
                select(RawSource.raw_data)
                .where(RawSource.run_id == run_id)
                .order_by(RawSource.created_at.desc())
                .limit(PROFILE_SAMPLE_LIMIT)
            )
            .scalars()
            .all()
        )

        field_stats: dict[str, dict[str, Any]] = {}
        profile_total = 0
        for raw_data in profile_sources:
            if not isinstance(raw_data, dict):
                continue
            profile_total += 1
            for key, value in raw_data.items():
                stat = field_stats.setdefault(
                    key,
                    {
                        "count": 0,
                        "types": set(),
                        "examples": [],
                        "example_fingerprints": set(),
                    },
                )
                stat["count"] += 1
                stat["types"].add(_value_type(value))
                if len(stat["examples"]) < 3:
                    preview = _preview_value(value)
                    fingerprint = _example_fingerprint(preview)
                    if fingerprint not in stat["example_fingerprints"]:
                        stat["examples"].append(preview)
                        stat["example_fingerprints"].add(fingerprint)

        field_profile = [
            RunFieldProfile(
                key=key,
                present_count=stat["count"],
                coverage_pct=round((stat["count"] / profile_total * 100.0), 2)
                if profile_total
                else 0.0,
                detected_types=sorted(list(stat["types"])),
                examples=stat["examples"],
            )
            for key, stat in sorted(
                field_stats.items(),
                key=lambda item: (-item[1]["count"], item[0]),
            )
        ]

        sample_rows = (
            session.execute(
                select(RawSource)
                .where(RawSource.run_id == run_id)
                .order_by(RawSource.created_at.desc())
                .limit(RECORD_SAMPLE_LIMIT)
            )
            .scalars()
            .all()
        )

        samples = [
            RunSampleRecord(
                raw_id=row.raw_id,
                created_at=_safe_iso(row.created_at),
                preview=_build_preview(row.raw_data if isinstance(row.raw_data, dict) else {}),
                raw_data=_trim_raw_data(row.raw_data if isinstance(row.raw_data, dict) else {}),
            )
            for row in sample_rows
        ]

        return RunDetailResponse(
            run={
                "id": str(run.id),
                "connector": run.connector,
                "job": run.job,
                "status": run.status,
                "cursor_start": run.cursor_start,
                "cursor_end": run.cursor_end,
                "items_fetched": run.items_fetched,
                "items_normalized": run.items_normalized,
                "errors": run.errors,
                "started_at": _safe_iso(run.created_at),
                "finished_at": _safe_iso(run.finished_at),
            },
            job=_build_job_info(run.connector, run.job),
            summary={
                "records_stored": records_stored,
                "distinct_raw_ids": distinct_raw_ids,
                "duplicate_raw_ids": duplicate_raw_ids,
                "first_record_at": _safe_iso(summary_row.first_record_at),
                "last_record_at": _safe_iso(summary_row.last_record_at),
                "profile_sampled_records": profile_total,
                "profile_sample_limit": PROFILE_SAMPLE_LIMIT,
            },
            field_profile=field_profile,
            samples=samples,
        )


# --- Re-normalize endpoints ---


@router.post("/normalize/rerun")
async def trigger_renormalize(connectors: Optional[str] = None):
    """Reset normalization flags and re-dispatch normalize tasks.

    Query params:
        connectors: comma-separated connector names (e.g. "camara,portal_transparencia").
                    If omitted, re-normalizes ALL connectors.
    """
    connector_list = [c.strip() for c in connectors.split(",") if c.strip()] if connectors else []

    with SyncSession() as session:
        # Find runs to re-normalize
        stmt = select(RawRun).where(RawRun.status == "completed")
        if connector_list:
            stmt = stmt.where(RawRun.connector.in_(connector_list))
        runs = session.execute(stmt).scalars().all()

        if not runs:
            return {"status": "nothing_to_rerun", "runs_dispatched": 0}

        # Reset normalized flag on affected RawSource records
        dispatched = []
        for run in runs:
            session.execute(
                RawSource.__table__.update()
                .where(RawSource.run_id == run.id)
                .values(normalized=False)
            )
            dispatched.append(str(run.id))

        session.commit()

    # Dispatch normalize_run tasks for each affected run
    for run_id in dispatched:
        celery_app.send_task(
            "worker.tasks.normalize_tasks.normalize_run",
            args=[run_id],
            queue="default",
        )

    return {
        "status": "dispatched",
        "runs_dispatched": len(dispatched),
        "run_ids": dispatched,
        "connectors_filter": connector_list or "all",
    }


# --- Entity Resolution endpoints ---


@router.post("/er/run")
async def trigger_er():
    """Trigger entity resolution pipeline."""
    result = celery_app.send_task(
        "worker.tasks.er_tasks.run_entity_resolution",
        queue="er",
    )
    return {"status": "dispatched", "task_id": result.id}


# --- Signal/Typology endpoints ---


@router.post("/signals/run")
async def trigger_all_signals():
    """Trigger all typology detectors."""
    result = celery_app.send_task(
        "worker.tasks.signal_tasks.run_all_signals",
        queue="signals",
    )
    return {"status": "dispatched", "task_id": result.id}


@router.post("/signals/run/{typology_code}")
async def trigger_single_signal(typology_code: str):
    """Trigger a single typology detector."""
    result = celery_app.send_task(
        "worker.tasks.signal_tasks.run_single_signal",
        args=[typology_code],
        queue="signals",
    )
    return {"status": "dispatched", "task_id": result.id, "typology": typology_code}


@router.post("/signals/replay/{signal_id}")
async def trigger_signal_replay(signal_id: uuid.UUID):
    """Deterministic replay checksum for a persisted signal/evidence package."""
    async def _run():
        async with async_session() as session:
            return await replay_signal(session, signal_id)

    replay = run_async(_run())
    if replay is None:
        raise HTTPException(status_code=404, detail="Signal not found")
    return replay.model_dump()


@router.get("/signals/quality")
async def signals_quality():
    """Monitoring metrics for explanatory quality and evidence pagination readiness."""
    async with async_session() as session:
        return await get_signal_quality_metrics(session)


@router.post("/backfill/signal-clarity")
async def trigger_signal_clarity_backfill():
    """Dispatch backfill for CATMAT enrichment + T03/T05 refresh + ER run."""
    result = celery_app.send_task(
        "worker.tasks.maintenance_tasks.backfill_signal_clarity",
        queue="default",
    )
    return {"status": "dispatched", "task_id": result.id}


@router.post("/backfill/public-profile-photos")
async def trigger_public_profile_photos_backfill():
    """Dispatch backfill to enrich missing official profile photos."""
    result = celery_app.send_task(
        "worker.tasks.maintenance_tasks.backfill_public_profile_photos",
        queue="default",
    )
    return {"status": "dispatched", "task_id": result.id}


# --- Baseline endpoints ---


@router.post("/baselines/compute")
async def trigger_baselines():
    """Trigger baseline computation."""
    result = celery_app.send_task(
        "worker.tasks.baseline_tasks.compute_all_baselines",
        queue="default",
    )
    return {"status": "dispatched", "task_id": result.id}


# --- Reference data endpoints ---


@router.post("/reference/seed")
async def trigger_seed_reference():
    """Trigger one-time population of reference_data table."""
    result = celery_app.send_task(
        "worker.tasks.reference_tasks.seed_reference_data",
        queue="default",
    )
    return {"status": "dispatched", "task_id": result.id}


@router.get("/reference/stats")
async def reference_stats():
    """Return counts of reference_data rows per category."""
    from shared.services.reference_seed import get_reference_stats

    with SyncSession() as session:
        stats = get_reference_stats(session)
    return stats


# --- Case endpoints ---


@router.post("/cases/build")
async def trigger_case_building():
    """Trigger case auto-creation from ungrouped signals."""
    from shared.services.case_builder import build_cases_from_signals

    with SyncSession() as session:
        cases = build_cases_from_signals(session)

    return {
        "status": "completed",
        "cases_created": len(cases),
        "case_ids": [str(c.id) for c in cases],
    }
