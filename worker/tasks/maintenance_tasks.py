"""Maintenance tasks for operational hygiene.

- Dead-letter logging for permanently failed tasks.
- Celery result backend cleanup.
- Stale run garbage collection.
"""
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import httpx
from celery import current_app, shared_task
from celery.signals import task_failure
from sqlalchemy import or_, select, update

from shared.logging import log

_MISSING_CLASSIFICATION_VALUES = {
    "",
    "unknown",
    "sem classificacao",
    "sem classificação",
    "null",
    "none",
    "nao_informado",
    "não informado",
}

_PHOTO_ATTR_KEYS = ("url_foto", "urlFoto", "photo_url", "UrlFotoParlamentar")


def _normalize_classification(value: object) -> str:
    text = str(value or "").strip()
    if text.lower() in _MISSING_CLASSIFICATION_VALUES:
        return "nao_informado"
    return text


def _existing_photo(attrs: dict | None) -> str | None:
    source = attrs or {}
    for key in _PHOTO_ATTR_KEYS:
        value = source.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _fetch_camara_photo(deputado_id: str, client: httpx.Client | None = None) -> str | None:
    if not deputado_id:
        return None
    try:
        def _do_fetch(c: httpx.Client) -> str | None:
            response = c.get(f"/deputados/{deputado_id}")
            response.raise_for_status()
            body = response.json() or {}
            dados = body.get("dados") or {}
            value = dados.get("urlFoto")
            if isinstance(value, str) and value.strip():
                return value.strip()
            return None

        if client is not None:
            return _do_fetch(client)
        with httpx.Client(
            base_url="https://dadosabertos.camara.leg.br/api/v2",
            headers={"Accept": "application/json"},
            timeout=20.0,
        ) as c:
            return _do_fetch(c)
    except Exception:
        return None


def _fetch_senado_photo_map() -> dict[str, str]:
    try:
        with httpx.Client(
            base_url="https://legis.senado.leg.br/dadosabertos",
            headers={"Accept": "application/json"},
            timeout=20.0,
        ) as client:
            response = client.get("/senador/lista/atual")
            response.raise_for_status()
            body = response.json() or {}
    except Exception:
        return {}

    parlamentares = (
        body.get("ListaParlamentarEmExercicio", {})
        .get("Parlamentares", {})
        .get("Parlamentar", [])
    )
    if isinstance(parlamentares, dict):
        parlamentares = [parlamentares]

    out: dict[str, str] = {}
    for parlamentar in parlamentares:
        ident = parlamentar.get("IdentificacaoParlamentar", parlamentar)
        code = str(ident.get("CodigoParlamentar", "")).strip()
        url = str(ident.get("UrlFotoParlamentar", "")).strip()
        if code and url:
            out[code] = url
    return out


@task_failure.connect
def _log_dead_letter(sender=None, task_id=None, exception=None, traceback=None, **kwargs):
    """Log permanently failed tasks (max retries exhausted) for DLQ analysis.

    This fires on every failure, but the retries field distinguishes
    transient failures (retries < max_retries) from dead letters.
    """
    retries = getattr(sender, "request", None)
    max_retries = getattr(sender, "max_retries", None)
    retry_count = retries.retries if retries else 0

    if max_retries is not None and retry_count >= max_retries:
        log.error(
            "dlq.dead_letter",
            task=sender.name if sender else "unknown",
            task_id=task_id,
            retries=retry_count,
            error=str(exception),
            error_type=type(exception).__name__,
        )


@shared_task(name="worker.tasks.maintenance_tasks.cleanup_stale_runs", soft_time_limit=300, time_limit=360, max_retries=1)
def cleanup_stale_runs(max_age_hours: int = 24):
    """Close orphaned 'running' RawRun entries older than max_age_hours.

    Containers may crash without marking runs as error. This catches them.
    """
    from shared.db_sync import SyncSession
    from shared.models.orm import RawRun

    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)

    with SyncSession() as session:
        stmt = (
            select(RawRun)
            .where(
                RawRun.status == "running",
                RawRun.created_at < cutoff,
            )
        )
        stale = session.execute(stmt).scalars().all()

        if not stale:
            log.info("cleanup_stale_runs.none_found")
            return {"status": "ok", "cleaned": 0}

        now = datetime.now(timezone.utc)
        for run in stale:
            run.status = "error"
            run.finished_at = now
            run.errors = {
                "error": f"stale run cleaned up after {max_age_hours}h",
                "error_type": "StaleRunCleanup",
            }

        session.commit()
        log.warning("cleanup_stale_runs.cleaned", count=len(stale))
        return {"status": "ok", "cleaned": len(stale)}


@shared_task(name="worker.tasks.maintenance_tasks.purge_old_results", soft_time_limit=300, time_limit=360, max_retries=1)
def purge_old_results(max_age_days: int = 7):
    """Remove old Celery result entries from Redis to reclaim memory.

    result_expires handles TTL at write time, but this catches any
    stragglers and provides explicit control.
    """
    from worker.worker_app import app as celery_app

    backend = celery_app.backend
    if hasattr(backend, "cleanup"):
        backend.cleanup()
        log.info("purge_old_results.done")
    else:
        log.info("purge_old_results.skip", reason="backend has no cleanup method")

    return {"status": "ok"}


@shared_task(name="worker.tasks.maintenance_tasks.backfill_signal_clarity", soft_time_limit=1800, time_limit=1900, max_retries=1)
def backfill_signal_clarity(max_events: int = 20000):
    """Backfill data quality for investigability and refresh CATMAT-dependent signals.

    Steps:
    1. Normalize missing CATMAT sentinel values to "nao_informado".
    2. Attempt CATMAT enrichment using source_pncp_id-linked events.
    3. Copy winner/bidder/supplier participants when target events have only buyer roles.
    4. Dispatch force-refresh for T01/T03/T05/T07 and run ER to materialize graph nodes/edges.
       T01 (HHI grouping), T03 (splitting threshold), T05 (price outlier), and T07 (cartel
       network) all use catmat_group/code for grouping and skip sentinel values — enriching
       CATMAT data directly improves signal recall for all four typologies.
    """
    from shared.db_sync import SyncSession
    from shared.models.orm import Event, EventParticipant
    from shared.repo.upsert_sync import upsert_participant_sync
    from worker.tasks.er_tasks import run_entity_resolution
    from worker.tasks.signal_tasks import run_single_signal

    log.info("backfill_signal_clarity.start", max_events=max_events)

    updated_catmat = 0
    enriched_catmat = 0
    enriched_participants = 0

    with SyncSession() as session:
        candidate_stmt = (
            select(Event)
            .where(
                Event.source_connector == "compras_gov",
                or_(
                    Event.attrs["catmat_group"].as_string().is_(None),
                    Event.attrs["catmat_group"].as_string().in_(
                        list(_MISSING_CLASSIFICATION_VALUES)
                    ),
                    Event.attrs["catmat_code"].as_string().is_(None),
                    Event.attrs["catmat_code"].as_string().in_(
                        list(_MISSING_CLASSIFICATION_VALUES)
                    ),
                ),
            )
            .limit(max_events)
        )
        events = session.execute(candidate_stmt).scalars().all()

        # Batch-preload related events by source_pncp_id to avoid N+1
        pncp_to_event = {}  # source_pncp_id -> list of events needing enrichment
        pncp_ids_to_query = set()
        for event in events:
            pncp_id = str((event.attrs or {}).get("source_pncp_id") or "").strip()
            if pncp_id:
                pncp_to_event[event.id] = pncp_id
                pncp_ids_to_query.add(pncp_id)

        related_by_pncp: dict[str, "Event"] = {}
        if pncp_ids_to_query:
            # Batch query: find related events by source_pncp_id
            _PNCP_BATCH = 500
            pncp_list = list(pncp_ids_to_query)
            for i in range(0, len(pncp_list), _PNCP_BATCH):
                batch = pncp_list[i : i + _PNCP_BATCH]
                related_stmt = (
                    select(Event)
                    .where(
                        or_(
                            Event.source_id.in_(batch),
                            Event.attrs["source_pncp_id"].as_string().in_(batch),
                        ),
                    )
                )
                for r in session.execute(related_stmt).scalars().all():
                    key = r.source_id or str((r.attrs or {}).get("source_pncp_id", ""))
                    if key and key not in related_by_pncp:
                        related_by_pncp[key] = r

        # Batch-preload participants for related events
        related_event_ids = [r.id for r in related_by_pncp.values()]
        parts_by_event: dict[str, list] = defaultdict(list)
        if related_event_ids:
            _PART_BATCH = 500
            for i in range(0, len(related_event_ids), _PART_BATCH):
                batch_eids = related_event_ids[i : i + _PART_BATCH]
                parts_stmt = select(EventParticipant).where(
                    EventParticipant.event_id.in_(batch_eids),
                    EventParticipant.role.in_(["winner", "bidder", "supplier"]),
                )
                for p in session.execute(parts_stmt).scalars().all():
                    parts_by_event[p.event_id].append(p)

        # Batch-preload existing roles for target events
        event_ids_list = [e.id for e in events]
        existing_roles_by_event: dict[str, set] = defaultdict(set)
        if event_ids_list:
            for i in range(0, len(event_ids_list), _PNCP_BATCH):
                batch_eids = event_ids_list[i : i + _PNCP_BATCH]
                roles_stmt = select(EventParticipant.event_id, EventParticipant.role).where(
                    EventParticipant.event_id.in_(batch_eids)
                )
                for eid, role in session.execute(roles_stmt).all():
                    existing_roles_by_event[eid].add(role)

        for event in events:
            attrs = dict(event.attrs or {})
            current_catmat = _normalize_classification(
                attrs.get("catmat_group") or attrs.get("catmat_code")
            )
            if attrs.get("catmat_group") != current_catmat:
                attrs["catmat_group"] = current_catmat
                updated_catmat += 1

            source_pncp_id = pncp_to_event.get(event.id)
            if source_pncp_id:
                related = related_by_pncp.get(source_pncp_id)
                if related is not None and related.id != event.id:
                    related_attrs = related.attrs or {}
                    related_catmat = _normalize_classification(
                        related_attrs.get("catmat_group") or related_attrs.get("catmat_code")
                    )
                    if current_catmat == "nao_informado" and related_catmat != "nao_informado":
                        attrs["catmat_group"] = related_catmat
                        current_catmat = related_catmat
                        enriched_catmat += 1

                    existing_roles = existing_roles_by_event.get(event.id, set())
                    has_business_roles = bool(existing_roles & {"winner", "bidder", "supplier"})
                    if not has_business_roles:
                        related_parts = parts_by_event.get(related.id, [])
                        for rp in related_parts:
                            upsert_participant_sync(
                                session,
                                event_id=event.id,
                                entity_id=rp.entity_id,
                                role=rp.role,
                                attrs=rp.attrs or {},
                            )
                            enriched_participants += 1

            event.attrs = attrs

        session.commit()

    t01_task = run_single_signal.delay("T01", dry_run=False, force_refresh=True).id
    t03_task = run_single_signal.delay("T03", dry_run=False, force_refresh=True).id
    t05_task = run_single_signal.delay("T05", dry_run=False, force_refresh=True).id
    t07_task = run_single_signal.delay("T07", dry_run=False, force_refresh=True).id
    er_task = run_entity_resolution.delay().id

    result = {
        "status": "dispatched",
        "events_scanned": len(events),
        "catmat_normalized": updated_catmat,
        "catmat_enriched": enriched_catmat,
        "participants_enriched": enriched_participants,
        "tasks": {
            "t01_refresh": t01_task,
            "t03_refresh": t03_task,
            "t05_refresh": t05_task,
            "t07_refresh": t07_task,
            "er_run": er_task,
        },
    }
    log.info("backfill_signal_clarity.done", **result)
    return result


@shared_task(
    name="worker.tasks.maintenance_tasks.trigger_post_ingest_recompute",
    bind=False,
)
def trigger_post_ingest_recompute(connector: str = "", job: str = "") -> dict:
    """Re-run baselines and signals after a major ingest completes.

    Called automatically after pt_beneficios (and other heavy jobs) finish
    full ingestion to ensure risk signals use the latest data.
    """
    from worker.tasks.baseline_tasks import compute_all_baselines
    from worker.tasks.signal_tasks import run_all_signals

    log.info(
        "trigger_post_ingest_recompute.start",
        connector=connector,
        job=job,
    )

    # Chain: baselines must complete before signals run (signals read baselines)
    from celery import chain, signature
    pipeline = chain(
        signature(
            "worker.tasks.baseline_tasks.compute_all_baselines",
            immutable=True,
            queue="default",
        ),
        signature(
            "worker.tasks.signal_tasks.run_all_signals",
            immutable=True,
            queue="signals",
        ),
    )
    result = pipeline.apply_async()

    log.info(
        "trigger_post_ingest_recompute.dispatched",
        connector=connector,
        job=job,
        chain_id=str(result.id),
    )
    return {
        "status": "dispatched",
        "connector": connector,
        "job": job,
        "chain_id": str(result.id),
    }


@shared_task(name="worker.tasks.maintenance_tasks.backfill_public_profile_photos", soft_time_limit=1800, time_limit=1900, max_retries=1)
def backfill_public_profile_photos(limit: int = 1000):
    """Populate missing public-profile photos for political entities."""
    from shared.db_sync import SyncSession
    from shared.models.orm import Entity

    log.info("backfill_public_profile_photos.start", limit=limit)

    senado_cache: dict[str, str] = {}
    senado_loaded = False
    scanned = 0
    updated = 0
    updated_camara = 0
    updated_senado = 0

    with SyncSession() as session:
        candidates = session.execute(
            select(Entity)
            .where(Entity.type == "person")
            .order_by(Entity.updated_at.desc())
            .limit(max(limit * 5, 200))
        ).scalars().all()

        camara_client = httpx.Client(
            base_url="https://dadosabertos.camara.leg.br/api/v2",
            headers={"Accept": "application/json"},
            timeout=20.0,
        )

        for entity in candidates:
            scanned += 1
            attrs = dict(entity.attrs or {})
            if _existing_photo(attrs):
                continue

            identifiers = entity.identifiers or {}
            photo_url = None
            source = None

            deputado_id = str(identifiers.get("deputado_id", "")).strip()
            if deputado_id:
                photo_url = _fetch_camara_photo(deputado_id, client=camara_client)
                source = "camara"

            if not photo_url:
                if not senado_loaded:
                    senado_cache = _fetch_senado_photo_map()
                    senado_loaded = True
                senador_code = str(
                    identifiers.get("codigo_parlamentar")
                    or identifiers.get("senator_id")
                    or ""
                ).strip()
                if senador_code:
                    photo_url = senado_cache.get(senador_code)
                    if photo_url:
                        source = "senado"

            if not photo_url:
                continue

            attrs["url_foto"] = photo_url
            attrs["photo_source"] = source or "official_public_api"
            entity.attrs = attrs

            updated += 1
            if source == "camara":
                updated_camara += 1
            if source == "senado":
                updated_senado += 1

            if updated >= limit:
                break

        camara_client.close()

        session.commit()

    result = {
        "status": "ok",
        "scanned": scanned,
        "updated": updated,
        "updated_camara": updated_camara,
        "updated_senado": updated_senado,
        "senado_cache_size": len(senado_cache),
    }
    log.info("backfill_public_profile_photos.done", **result)
    return result


@shared_task(
    name="worker.tasks.maintenance_tasks.run_full_pipeline",
    bind=False,
    max_retries=0,
)
def run_full_pipeline() -> dict:
    """Dispatch ER → baselines → signals as a Celery chain."""
    from celery import chain, signature

    pipeline = chain(
        signature(
            "worker.tasks.er_tasks.run_entity_resolution",
            immutable=True,
            queue="er",
        ),
        signature(
            "worker.tasks.baseline_tasks.compute_all_baselines",
            immutable=True,
            queue="default",
        ),
        signature(
            "worker.tasks.signal_tasks.run_all_signals",
            immutable=True,
            queue="signals",
        ),
    )
    result = pipeline.apply_async()
    log.info("run_full_pipeline.dispatched", chain_id=str(result.id))
    return {"status": "dispatched", "chain_id": str(result.id)}


@shared_task(
    name="worker.tasks.maintenance_tasks.vacuum_raw_source",
    bind=False,
    max_retries=1,
    soft_time_limit=600,
    time_limit=660,
)
def vacuum_raw_source() -> dict:
    """VACUUM raw_source to reclaim disk space from cleared raw_data fields.

    Must run outside a transaction (AUTOCOMMIT). Uses a dedicated engine
    connection to avoid interfering with the normal session pool.
    """
    from sqlalchemy import text
    from shared.db_sync import sync_engine

    with sync_engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        conn.execute(text("VACUUM raw_source"))

    log.info("vacuum_raw_source.done")
    return {"status": "ok"}


def _watchdog_recover_orphans() -> dict | None:
    """Recover orphaned 'running' runs older than 10 min. Returns result dict or None."""
    from shared.db_sync import SyncSession
    from shared.models.orm import IngestState, RawRun

    try:
        with SyncSession() as session:
            orphan_cutoff = datetime.now(timezone.utc) - timedelta(minutes=10)
            orphans = session.execute(
                select(RawRun).where(
                    RawRun.status == "running",
                    RawRun.finished_at.is_(None),
                    RawRun.created_at < orphan_cutoff,
                )
            ).scalars().all()

            if not orphans:
                return None

            now_ts = datetime.now(timezone.utc)
            seen: set[tuple[str, str]] = set()
            for run in orphans:
                run.status = "error"
                run.finished_at = now_ts
                run.errors = {
                    "error": "stale run recovered by watchdog",
                    "error_type": "StaleRunWatchdog",
                    "auto_recovered": True,
                }
                seen.add((run.connector, run.job))
            session.commit()
            log.warning("pipeline_watchdog.orphans_recovered", count=len(orphans))

            for connector, job in seen:
                state = session.execute(
                    select(IngestState).where(
                        IngestState.connector == connector,
                        IngestState.job == job,
                    )
                ).scalar_one_or_none()
                cursor = state.last_cursor if state else None
                from worker.tasks.ingest_tasks import ingest_connector
                ingest_connector.apply_async(
                    args=[connector, job, cursor],
                    queue="ingest",
                    countdown=10,
                )

            return {"status": "recovered_orphans", "count": len(orphans), "redispatched": len(seen)}
    except Exception as exc:
        log.warning("pipeline_watchdog.orphan_recovery_failed", error=str(exc))
        return None


@shared_task(
    name="worker.tasks.maintenance_tasks.pipeline_watchdog",
    bind=False,
    soft_time_limit=60,
    time_limit=90,
    max_retries=0,
)
def pipeline_watchdog() -> dict:
    """Check DB state every 15 min and drive the full pipeline.

    Two triggers:
    1. ER stale (new ingest data not yet entity-resolved) → run_full_pipeline
       (ER → baselines → signals).
    2. Procurement data exists but baselines are absent → dispatch baselines +
       signals immediately, even when ER is up-to-date. This fires the signal
       pipeline as soon as PNCP/comprasnet data normalises, without waiting for
       the next ER run watermark update.
    """
    from sqlalchemy import func, select

    from shared.db_sync import SyncSession
    from shared.models.orm import BaselineSnapshot, ERRunState, Event, RawRun

    # ── Auto-recover orphaned runs (safety net) ─────────────────────
    recovery = _watchdog_recover_orphans()
    if recovery is not None:
        return recovery

    with SyncSession() as session:
        # Skip immediately if any ingest job is still running — data is incomplete.
        ingest_running_count = session.execute(
            select(func.count()).select_from(RawRun).where(RawRun.status == "running")
        ).scalar_one()
        if ingest_running_count > 0:
            log.info("pipeline_watchdog.skip", reason="ingest_running", count=ingest_running_count)
            return {"status": "skip", "reason": "ingest_running"}

        er_running = session.execute(
            select(ERRunState).where(ERRunState.status == "running").limit(1)
        ).scalar_one_or_none()
        if er_running is not None:
            log.info("pipeline_watchdog.skip", reason="er_running")
            return {"status": "skip", "reason": "er_running"}

        last_ingest_at = session.execute(
            select(func.max(RawRun.finished_at)).where(RawRun.status == "completed")
        ).scalar_one()
        if last_ingest_at is None:
            log.info("pipeline_watchdog.skip", reason="no_completed_ingest")
            return {"status": "skip", "reason": "no_completed_ingest"}

        er_completed = session.execute(
            select(ERRunState)
            .where(ERRunState.status == "completed", ERRunState.watermark_at.is_not(None))
            .order_by(ERRunState.watermark_at.desc())
            .limit(1)
        ).scalar_one_or_none()

        if er_completed is not None and er_completed.watermark_at >= last_ingest_at:
            # ER is up-to-date with latest ingest. Check if procurement data
            # appeared since baselines were last computed.
            procurement_count = session.execute(
                select(func.count()).select_from(Event).where(
                    Event.type.in_(["licitacao", "contrato"])
                )
            ).scalar_one()

            if procurement_count > 0:
                baseline_count = session.execute(
                    select(func.count()).select_from(BaselineSnapshot)
                ).scalar_one()

                if baseline_count == 0:
                    from celery import chain, signature
                    pipeline = chain(
                        signature(
                            "worker.tasks.baseline_tasks.compute_all_baselines",
                            immutable=True,
                            queue="default",
                        ),
                        signature(
                            "worker.tasks.signal_tasks.run_all_signals",
                            immutable=True,
                            queue="signals",
                        ),
                    )
                    result = pipeline.apply_async()
                    log.info(
                        "pipeline_watchdog.dispatched_baselines",
                        procurement_events=procurement_count,
                        chain_id=str(result.id),
                    )
                    return {
                        "status": "dispatched_baselines",
                        "procurement_events": procurement_count,
                        "chain_id": str(result.id),
                    }

            log.info("pipeline_watchdog.skip", reason="er_up_to_date")
            return {"status": "skip", "reason": "er_up_to_date"}

    result = run_full_pipeline.apply_async(queue="default")
    log.info("pipeline_watchdog.dispatched", task_id=str(result.id))
    return {"status": "dispatched", "task_id": str(result.id)}
