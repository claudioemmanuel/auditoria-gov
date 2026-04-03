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

from openwatch_utils.logging import log

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
        try:
            from openwatch_services.infra_alerts import _send_infra_alert
            _send_infra_alert(
                "dead_letter",
                task=sender.name if sender else "unknown",
                error=str(exception),
                retries=retry_count,
            )
        except Exception:  # noqa: BLE001
            pass


@shared_task(name="openwatch_pipelines.maintenance_tasks.cleanup_stale_runs", soft_time_limit=300, time_limit=360, max_retries=1)
def cleanup_stale_runs(max_age_hours: int = 24):
    """Close orphaned 'running' RawRun entries older than max_age_hours.

    Containers may crash without marking runs as error. This catches them.
    """
    from openwatch_db.db_sync import SyncSession
    from openwatch_models.orm import RawRun

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


@shared_task(name="openwatch_pipelines.maintenance_tasks.purge_old_results", soft_time_limit=300, time_limit=360, max_retries=1)
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


@shared_task(name="openwatch_pipelines.maintenance_tasks.backfill_signal_clarity", soft_time_limit=1800, time_limit=1900, max_retries=1)
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
    from openwatch_db.db_sync import SyncSession
    from openwatch_models.orm import Event, EventParticipant
    from openwatch_db.upsert_sync import upsert_participant_sync
    from openwatch_pipelines.er_tasks import run_entity_resolution
    from openwatch_pipelines.signal_tasks import run_single_signal

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
    name="openwatch_pipelines.maintenance_tasks.trigger_post_ingest_recompute",
    bind=False,
)
def trigger_post_ingest_recompute(connector: str = "", job: str = "") -> dict:
    """Re-run baselines and signals after a major ingest completes.

    Called automatically after pt_beneficios (and other heavy jobs) finish
    full ingestion to ensure risk signals use the latest data.
    """
    from openwatch_pipelines.baseline_tasks import compute_all_baselines
    from openwatch_pipelines.signal_tasks import run_all_signals

    log.info(
        "trigger_post_ingest_recompute.start",
        connector=connector,
        job=job,
    )

    # Chain: baselines must complete before signals run (signals read baselines)
    from celery import chain, signature
    pipeline = chain(
        signature(
            "openwatch_pipelines.baseline_tasks.compute_all_baselines",
            immutable=True,
            queue="default",
        ),
        signature(
            "openwatch_pipelines.signal_tasks.run_all_signals",
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


@shared_task(name="openwatch_pipelines.maintenance_tasks.backfill_public_profile_photos", soft_time_limit=1800, time_limit=1900, max_retries=1)
def backfill_public_profile_photos(limit: int = 1000):
    """Populate missing public-profile photos for political entities."""
    from openwatch_db.db_sync import SyncSession
    from openwatch_models.orm import Entity

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
    name="openwatch_pipelines.maintenance_tasks.run_full_pipeline",
    bind=False,
    max_retries=0,
)
def run_full_pipeline() -> dict:
    """Dispatch ER → baselines → signals as a Celery chain."""
    from celery import chain, signature

    pipeline = chain(
        signature(
            "openwatch_pipelines.er_tasks.run_entity_resolution",
            immutable=True,
            queue="er",
        ),
        signature(
            "openwatch_pipelines.baseline_tasks.compute_all_baselines",
            immutable=True,
            queue="default",
        ),
        signature(
            "openwatch_pipelines.signal_tasks.run_all_signals",
            immutable=True,
            queue="signals",
        ),
    )
    result = pipeline.apply_async()
    log.info("run_full_pipeline.dispatched", chain_id=str(result.id))
    return {"status": "dispatched", "chain_id": str(result.id)}


@shared_task(
    name="openwatch_pipelines.maintenance_tasks.vacuum_raw_source",
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
    from openwatch_db.db_sync import sync_engine

    with sync_engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        conn.execute(text("VACUUM ANALYZE raw_source"))

    log.info("vacuum_raw_source.done")
    return {"status": "ok"}


@shared_task(
    name="openwatch_pipelines.maintenance_tasks.purge_normalized_raw_source",
    bind=False,
    max_retries=1,
    soft_time_limit=1800,
    time_limit=1900,
)
def purge_normalized_raw_source(batch_size: int = 10_000) -> dict:
    """Delete raw_source rows that have already been normalized.

    Rows with normalized=True have raw_data={} and are no longer needed.
    Entity/event data is safely stored in the entity/event tables.
    entity_raw_source links are cascade-deleted, which is acceptable because
    provenance is still traceable via raw_run (connector, job, cursor range).

    Runs in batches to avoid long-running transactions and lock contention.
    """
    from sqlalchemy import text
    from openwatch_db.db_sync import SyncSession

    total_deleted = 0
    with SyncSession() as session:
        while True:
            result = session.execute(
                text(
                    "DELETE FROM raw_source WHERE id IN ("
                    "  SELECT id FROM raw_source WHERE normalized = true LIMIT :limit"
                    ")"
                ),
                {"limit": batch_size},
            )
            session.commit()
            deleted = result.rowcount
            total_deleted += deleted
            log.info("purge_normalized_raw_source.batch", deleted=deleted, total=total_deleted)
            if deleted < batch_size:
                break

    log.info("purge_normalized_raw_source.done", total_deleted=total_deleted)
    return {"status": "ok", "deleted": total_deleted}


# Disk-usage thresholds (% of VM disk used)
_DISK_WARN_PCT = 50       # emit warning log (was 60)
_DISK_THROTTLE_PCT = 60   # set Redis flag, trigger cleanup (was 70)
_DISK_HARD_STOP_GB = 5.0  # absolute floor — ingest gate refuses below this
_DISK_THROTTLE_KEY = "disk:throttle"
_DISK_THROTTLE_TTL = 3600  # 1 hour; watchdog will renew or clear each cycle


def _cleanup_bulk_dirs() -> list[str]:
    """Remove processed bulk files (TSE/Receita) that are already staged in raw_source.

    Called automatically by disk_space_watchdog when usage >= _DISK_THROTTLE_PCT.
    Returns list of deleted file paths.
    """
    import glob
    import os

    from openwatch_config.settings import settings

    deleted: list[str] = []
    for data_dir in [settings.TSE_DATA_DIR, settings.RECEITA_CNPJ_DATA_DIR]:
        if not os.path.isdir(data_dir):
            continue
        for fpath in glob.glob(os.path.join(data_dir, "**", "*"), recursive=True):
            if not os.path.isfile(fpath):
                continue
            try:
                os.remove(fpath)
                deleted.append(fpath)
                log.info("cleanup_bulk_dirs.deleted", path=fpath)
            except OSError as exc:
                log.warning("cleanup_bulk_dirs.failed", path=fpath, error=str(exc))
    return deleted


@shared_task(
    name="openwatch_pipelines.maintenance_tasks.disk_space_watchdog",
    bind=False,
    max_retries=0,
    soft_time_limit=60,
    time_limit=90,
)
def disk_space_watchdog() -> dict:
    """Monitor Docker VM disk, CPU, and memory; proactively free space before Postgres panics.

    Disk checks shutil.disk_usage("/") which reflects the shared vda1 Docker VM disk.
    At >= DISK_THROTTLE_PCT: sets Redis key disk:throttle=1, triggers purge + vacuum + bulk cleanup.
    Memory checks psutil.virtual_memory().  At >= MEM_BLOCK_PCT: sets memory:throttle Redis key
    which gates ingest tasks.  At >= MEM_WARN_PCT: logs warning.
    CPU checks psutil.cpu_percent(interval=1).  At >= CPU_WARN_PCT: logs warning + sends alert.
    """
    import os
    import shutil

    import psutil
    import redis as redis_lib

    from openwatch_config.settings import settings

    MEM_WARN_PCT = int(os.environ.get("MEM_WARN_PCT", "75"))
    MEM_BLOCK_PCT = int(os.environ.get("MEM_BLOCK_PCT", "85"))
    CPU_WARN_PCT = int(os.environ.get("CPU_WARN_PCT", "85"))
    _MEM_THROTTLE_KEY = "memory:throttle"
    _MEM_THROTTLE_TTL = 3600  # 1 h; watchdog renews or clears each cycle

    stat = shutil.disk_usage("/")
    pct_used = (stat.used / stat.total) * 100
    free_gb = stat.free / 1e9

    # CPU — non-blocking 1 s sample (uses cached kernel stat)
    cpu_pct = psutil.cpu_percent(interval=1)

    # Memory
    mem = psutil.virtual_memory()
    mem_pct = mem.percent

    log.info(
        "disk_space_watchdog.status",
        pct_used=round(pct_used, 1),
        free_gb=round(free_gb, 2),
        total_gb=round(stat.total / 1e9, 2),
        cpu_pct=round(cpu_pct, 1),
        mem_pct=round(mem_pct, 1),
    )

    try:
        r = redis_lib.from_url(settings.REDIS_URL, socket_connect_timeout=5)

        # ── Disk ──────────────────────────────────────────────────────
        if pct_used >= _DISK_THROTTLE_PCT or free_gb < _DISK_HARD_STOP_GB:
            r.set(_DISK_THROTTLE_KEY, "1", ex=_DISK_THROTTLE_TTL)
            log.warning(
                "disk_space_watchdog.throttle_enabled",
                pct_used=round(pct_used, 1),
                free_gb=round(free_gb, 2),
            )
            # Proactive cleanup: purge dead rows and bulk files
            purge_normalized_raw_source.apply_async(queue="vacuum")
            vacuum_raw_source.apply_async(queue="vacuum")
            deleted = _cleanup_bulk_dirs()
            log.info("disk_space_watchdog.bulk_cleanup", files_deleted=len(deleted))
        else:
            r.delete(_DISK_THROTTLE_KEY)
            if pct_used >= _DISK_WARN_PCT:
                log.warning(
                    "disk_space_watchdog.high_usage",
                    pct_used=round(pct_used, 1),
                    free_gb=round(free_gb, 2),
                )
                # Proactive: clean bulk dirs at warn level, not just throttle
                deleted = _cleanup_bulk_dirs()
                if deleted:
                    log.info("disk_space_watchdog.warn_bulk_cleanup", files_deleted=len(deleted))

        # ── Memory ────────────────────────────────────────────────────
        if mem_pct >= MEM_BLOCK_PCT:
            r.setex(_MEM_THROTTLE_KEY, _MEM_THROTTLE_TTL, "1")
            log.warning(
                "system_health.memory_throttle_set",
                pct=round(mem_pct, 1),
                available_gb=round(mem.available / 1e9, 2),
            )
            try:
                from openwatch_services.infra_alerts import _send_infra_alert
                _send_infra_alert("memory_throttle", pct=round(mem_pct, 1))
            except Exception:  # noqa: BLE001
                pass
        elif mem_pct >= MEM_WARN_PCT:
            log.warning("system_health.memory_warn", pct=round(mem_pct, 1))
        else:
            r.delete(_MEM_THROTTLE_KEY)

        # ── CPU ───────────────────────────────────────────────────────
        if cpu_pct >= CPU_WARN_PCT:
            log.warning("system_health.cpu_high", pct=round(cpu_pct, 1))
            try:
                from openwatch_services.infra_alerts import _send_infra_alert
                _send_infra_alert("cpu_high", pct=round(cpu_pct, 1))
            except Exception:  # noqa: BLE001
                pass

    except Exception as exc:  # noqa: BLE001
        # Redis unavailable: fail open, log and continue
        log.warning("disk_space_watchdog.redis_error", error=str(exc))

    return {
        "disk_pct": round(pct_used, 1),
        "free_gb": round(free_gb, 2),
        "total_gb": round(stat.total / 1e9, 2),
        "cpu_pct": round(cpu_pct, 1),
        "mem_pct": round(mem_pct, 1),
    }


def _watchdog_recover_orphans() -> dict | None:
    """Recover orphaned 'running' runs older than 2 hours. Returns result dict or None.

    2-hour threshold: ingest jobs legitimately run for 30–90 min (PNCP cursor
    pagination, bulk downloads). 10 min was too aggressive and killed healthy jobs.
    The daily cleanup_stale_runs task (24h cutoff) handles truly dead runs.
    """
    from openwatch_db.db_sync import SyncSession
    from openwatch_models.orm import IngestState, RawRun

    try:
        with SyncSession() as session:
            orphan_cutoff = datetime.now(timezone.utc) - timedelta(hours=2)
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
                from openwatch_pipelines.ingest_tasks import ingest_connector
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
    name="openwatch_pipelines.maintenance_tasks.pipeline_watchdog",
    bind=False,
    soft_time_limit=60,
    time_limit=90,
    max_retries=0,
)
def pipeline_watchdog() -> dict:
    """Check DB state every 5 min and drive the full pipeline.

    Three triggers:
    1. ER stale (new ingest data not yet entity-resolved) → run_full_pipeline
       (ER → baselines → signals).
    2. ER up-to-date + procurement events exist → dispatch baselines → signals
       chain. Both are incremental: baselines skip types with no new events,
       signals skip typologies with no new data. Cheap no-op when nothing changed.
    3. Orphan recovery: auto-recover stale "running" RawRun entries older than 2h.
    """
    from sqlalchemy import func, select

    from openwatch_db.db_sync import SyncSession
    from openwatch_models.orm import BaselineSnapshot, ERRunState, Event, RawRun, RawSource

    # ── Auto-recover orphaned runs (safety net) ─────────────────────
    recovery = _watchdog_recover_orphans()
    if recovery is not None:
        return recovery

    with SyncSession() as session:
        # ER is incremental (watermark_at) and holds an advisory lock, so it
        # is safe to run alongside ingest.  Do NOT skip when ingest is running
        # — the pipeline must advance continuously like an assembly line.
        ingest_running_count = session.execute(
            select(func.count()).select_from(RawRun).where(RawRun.status == "running")
        ).scalar_one()

        er_running = session.execute(
            select(ERRunState).where(ERRunState.status == "running").limit(1)
        ).scalar_one_or_none()

        if er_running is not None:
            # Check if this ER run is genuinely in-progress or stale (crashed worker).
            # Any 'running' state older than 9000 s must be from a dead worker —
            # Celery's hard_time_limit=7500 s would have killed it by then.
            from sqlalchemy import text as _text
            stale_threshold = datetime.now(timezone.utc) - timedelta(seconds=9000)
            if er_running.created_at < stale_threshold:
                can_lock = session.execute(
                    _text("SELECT pg_try_advisory_lock(7349812)")
                ).scalar()
                if can_lock:
                    er_running.status = "failed"
                    session.commit()
                    session.execute(_text("SELECT pg_advisory_unlock(7349812)"))
                    age_s = (datetime.now(timezone.utc) - er_running.created_at).total_seconds()
                    log.warning(
                        "pipeline_watchdog.er_stale_recovered",
                        er_id=str(er_running.id),
                        age_seconds=round(age_s),
                    )
                    try:
                        from openwatch_services.infra_alerts import _send_infra_alert
                        _send_infra_alert(
                            "er_stale_recovered",
                            source="watchdog",
                            er_id=str(er_running.id),
                            auto_resolved=True,
                        )
                    except Exception:  # noqa: BLE001
                        pass
                    er_running = None  # fall through — treat as if ER is idle

            if er_running is not None:
                log.info("pipeline_watchdog.skip", reason="er_running")
                return {"status": "skip", "reason": "er_running"}

        # Include "yielded" runs — they produced data even if time-sliced.
        last_ingest_at = session.execute(
            select(func.max(RawRun.finished_at)).where(
                RawRun.status.in_(["completed", "yielded"])
            )
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

        # ── Check if baselines/signals need running (independent of ER staleness) ──
        procurement_count = session.execute(
            select(func.count()).select_from(Event).where(
                Event.type.in_(["licitacao", "contrato"])
            )
        ).scalar_one()

        baseline_count = session.execute(
            select(func.count()).select_from(BaselineSnapshot)
        ).scalar_one()

        if er_completed is not None and er_completed.watermark_at >= last_ingest_at:
            # ER is up-to-date with latest ingest.
            # Dispatch baselines → signals chain.  Both are now incremental:
            # baselines skip types with no new events, signals skip typologies
            # with no new data.  Cheap no-op when nothing changed.
            if procurement_count > 0:
                from celery import chain, signature
                pipeline = chain(
                    signature(
                        "openwatch_pipelines.baseline_tasks.compute_all_baselines",
                        immutable=True,
                        queue="default",
                    ),
                    signature(
                        "openwatch_pipelines.signal_tasks.run_all_signals",
                        immutable=True,
                        queue="signals",
                    ),
                )
                result = pipeline.apply_async()
                log.info(
                    "pipeline_watchdog.dispatched_baselines_signals",
                    procurement_events=procurement_count,
                    baseline_count=baseline_count,
                    chain_id=str(result.id),
                )
                return {
                    "status": "dispatched_baselines_signals",
                    "procurement_events": procurement_count,
                    "chain_id": str(result.id),
                }

            log.info("pipeline_watchdog.skip", reason="er_up_to_date_no_procurement")
            return {"status": "skip", "reason": "er_up_to_date_no_procurement"}

        # ── Backlog prediction ─────────────────────────────────────────────
        import json
        import time as _time

        import redis as redis_lib
        from sqlalchemy import func as _func

        from openwatch_config.settings import settings as _settings

        BACKLOG_LIMIT = 1_000_000
        BACKLOG_WARN_ETA_MINUTES = int(
            __import__("os").environ.get("BACKLOG_WARN_ETA_MINUTES", "30")
        )

        current_backlog = session.execute(
            select(_func.count()).select_from(RawSource).where(RawSource.normalized == False)  # noqa: E712
        ).scalar_one()

        try:
            _r = redis_lib.from_url(_settings.REDIS_URL, socket_connect_timeout=5)
            sample = json.dumps({"t": _time.time(), "v": current_backlog})
            _r.lpush("backlog:samples", sample)
            _r.ltrim("backlog:samples", 0, 11)   # keep last 12 samples (~60 min at 5 min watchdog)
            _r.expire("backlog:samples", 7200)

            raw_samples = _r.lrange("backlog:samples", 0, 5)   # last 6 = 30 min
            if len(raw_samples) >= 2:
                newest = json.loads(raw_samples[0])
                oldest = json.loads(raw_samples[-1])
                elapsed_min = max((newest["t"] - oldest["t"]) / 60, 0.1)
                growth_rate = (newest["v"] - oldest["v"]) / elapsed_min  # rows/min

                if growth_rate > 0:
                    eta_minutes = (BACKLOG_LIMIT - current_backlog) / growth_rate
                    log.info(
                        "backlog.trend",
                        current=current_backlog,
                        rate_per_min=round(growth_rate, 1),
                        eta_minutes=round(eta_minutes, 1),
                    )
                    if eta_minutes < BACKLOG_WARN_ETA_MINUTES:
                        log.warning(
                            "backlog.approaching_limit",
                            current=current_backlog,
                            rate_per_min=round(growth_rate, 1),
                            eta_minutes=round(eta_minutes, 1),
                        )
                        try:
                            from openwatch_services.infra_alerts import _send_infra_alert
                            _send_infra_alert(
                                "backlog_critical",
                                current=current_backlog,
                                rate_per_min=round(growth_rate, 1),
                                eta_minutes=round(eta_minutes, 1),
                            )
                        except Exception:  # noqa: BLE001
                            pass
                        # Pre-emptive drain — don't wait for the 3 h scheduled task
                        trigger_normalize_drain.apply_async(queue="vacuum", countdown=5)
        except Exception as exc:  # noqa: BLE001
            log.warning("backlog.trend_error", error=str(exc))

        # ── ER is stale or never ran — dispatch full pipeline ──────────
        # Even if ingest is running, ER is incremental (watermark_at) and
        # holds an advisory lock, so concurrent dispatch is safe.
        log.info(
            "pipeline_watchdog.er_stale",
            ingest_running=ingest_running_count,
            er_watermark=str(er_completed.watermark_at) if er_completed else None,
            last_ingest=str(last_ingest_at),
        )
    result = run_full_pipeline.apply_async(queue="default")
    log.info("pipeline_watchdog.dispatched", task_id=str(result.id))
    return {"status": "dispatched", "task_id": str(result.id)}


@shared_task(
    name="openwatch_pipelines.maintenance_tasks.purge_stale_t02_signals",
    bind=False,
    max_retries=1,
    soft_time_limit=600,
    time_limit=700,
)
def purge_stale_t02_signals() -> dict:
    """Deleta sinais T02 vinculados a licitações dispensa ou situação void.

    Deve ser executada UMA VEZ após o refinamento das regras de T02.
    Os ~300 sinais gerados para eventos dispensa são falsos positivos
    que devem ser removidos antes do reprocessamento limpo.
    """
    from sqlalchemy import text

    from openwatch_db.db_sync import SyncSession

    with SyncSession() as session:
        result = session.execute(text("""
            DELETE FROM risk_signal rs
            USING typology t,
                  signal_event se,
                  event e
            WHERE rs.typology_id = t.id
              AND t.code = 'T02'
              AND se.signal_id = rs.id
              AND e.id = se.event_id
              AND (
                  lower(e.attrs->>'modality') LIKE '%dispensa%'
                  OR lower(e.attrs->>'modality') LIKE '%inexigibilidade%'
                  OR lower(e.attrs->>'situacao') IN (
                      'deserta', 'fracassada', 'revogada', 'anulada', 'cancelada'
                  )
              )
        """))
        session.commit()
        deleted = result.rowcount

    log.info("purge_stale_t02_signals.done", deleted=deleted)
    return {"status": "ok", "deleted": deleted}


@shared_task(
    name="openwatch_pipelines.maintenance_tasks.trigger_normalize_drain",
    bind=False,
    max_retries=0,
    soft_time_limit=60,
    time_limit=90,
)
def trigger_normalize_drain() -> dict:
    """Dispatch extra normalize tasks when the raw_source backlog is large.

    When more than 500K rows are pending normalization, the regular per-run
    normalize tasks may not drain the backlog fast enough. This task finds all
    raw_runs with unnormalized rows and re-dispatches normalize_run for each,
    effectively scaling out normalization work without adding new workers.

    Safe to call multiple times — normalize_run is idempotent (it queries
    normalized=False rows; if none remain, it returns immediately).
    """
    from sqlalchemy import text

    from openwatch_db.db_sync import SyncSession

    with SyncSession() as session:
        backlog = session.execute(
            text("SELECT COUNT(*) FROM raw_source WHERE normalized = false")
        ).scalar() or 0

        if backlog < 500_000:
            log.info("trigger_normalize_drain.skipped", backlog=backlog, threshold=500_000)
            return {"status": "skipped", "backlog": backlog}

        # Find all raw_runs that still have unnormalized rows
        pending_runs = session.execute(
            text(
                "SELECT DISTINCT run_id FROM raw_source WHERE normalized = false"
            )
        ).scalars().all()

    dispatched = 0
    from openwatch_pipelines.normalize_tasks import normalize_run
    for run_id in pending_runs:
        normalize_run.apply_async(args=[str(run_id)], queue="normalize")
        dispatched += 1

    log.warning(
        "trigger_normalize_drain.dispatched",
        backlog=backlog,
        normalize_runs_dispatched=dispatched,
    )
    return {"status": "dispatched", "backlog": backlog, "runs": dispatched}


@shared_task(
    name="openwatch_pipelines.maintenance_tasks.docker_build_prune",
    bind=False,
    max_retries=0,
    soft_time_limit=120,
    time_limit=150,
)
def docker_build_prune() -> dict:
    """Prune Docker build cache to prevent unbounded disk growth.

    Docker build cache can accumulate 10-15 GB over time from repeated image
    rebuilds. This task runs weekly via Beat to keep it under control.
    Requires the Docker socket to be accessible inside the worker container,
    or falls back to a no-op with a warning if docker CLI is unavailable.
    """
    import subprocess

    try:
        result = subprocess.run(
            ["docker", "buildx", "prune", "-f"],
            capture_output=True,
            text=True,
            timeout=100,
        )
        stdout_tail = result.stdout[-500:] if result.stdout else ""
        log.info(
            "docker_build_prune.done",
            returncode=result.returncode,
            output=stdout_tail,
        )
        return {"status": "ok", "returncode": result.returncode}
    except FileNotFoundError:
        log.warning("docker_build_prune.skipped", reason="docker CLI not available in container")
        return {"status": "skipped", "reason": "docker CLI not available"}
    except subprocess.TimeoutExpired:
        log.warning("docker_build_prune.timeout")
        return {"status": "timeout"}
