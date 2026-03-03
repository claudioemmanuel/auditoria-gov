"""Maintenance tasks for operational hygiene.

- Dead-letter logging for permanently failed tasks.
- Celery result backend cleanup.
- Stale run garbage collection.
"""
from datetime import datetime, timedelta, timezone

import httpx
from celery import shared_task
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


def _fetch_camara_photo(deputado_id: str) -> str | None:
    if not deputado_id:
        return None
    try:
        with httpx.Client(
            base_url="https://dadosabertos.camara.leg.br/api/v2",
            headers={"Accept": "application/json"},
            timeout=20.0,
        ) as client:
            response = client.get(f"/deputados/{deputado_id}")
            response.raise_for_status()
            body = response.json() or {}
            dados = body.get("dados") or {}
            value = dados.get("urlFoto")
            if isinstance(value, str) and value.strip():
                return value.strip()
    except Exception:
        return None
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


@shared_task(name="worker.tasks.maintenance_tasks.cleanup_stale_runs")
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


@shared_task(name="worker.tasks.maintenance_tasks.purge_old_results")
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


@shared_task(name="worker.tasks.maintenance_tasks.backfill_signal_clarity")
def backfill_signal_clarity(max_events: int = 20000):
    """Backfill data quality for investigability and refresh T03/T05 signals.

    Steps:
    1. Normalize missing CATMAT sentinel values to "nao_informado".
    2. Attempt CATMAT enrichment using source_pncp_id-linked events.
    3. Copy winner/bidder/supplier participants when target events have only buyer roles.
    4. Dispatch force-refresh for T03/T05 and run ER to materialize graph nodes/edges.
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

        for event in events:
            attrs = dict(event.attrs or {})
            current_catmat = _normalize_classification(
                attrs.get("catmat_group") or attrs.get("catmat_code")
            )
            if attrs.get("catmat_group") != current_catmat:
                attrs["catmat_group"] = current_catmat
                updated_catmat += 1

            source_pncp_id = str(attrs.get("source_pncp_id") or "").strip()
            if source_pncp_id:
                related_stmt = (
                    select(Event)
                    .where(
                        Event.id != event.id,
                        or_(
                            Event.source_id == source_pncp_id,
                            Event.attrs["source_pncp_id"].as_string() == source_pncp_id,
                        ),
                    )
                    .limit(1)
                )
                related = session.execute(related_stmt).scalar_one_or_none()
                if related is not None:
                    related_attrs = related.attrs or {}
                    related_catmat = _normalize_classification(
                        related_attrs.get("catmat_group") or related_attrs.get("catmat_code")
                    )
                    if current_catmat == "nao_informado" and related_catmat != "nao_informado":
                        attrs["catmat_group"] = related_catmat
                        current_catmat = related_catmat
                        enriched_catmat += 1

                    existing_roles = set(
                        session.execute(
                            select(EventParticipant.role).where(
                                EventParticipant.event_id == event.id
                            )
                        ).scalars().all()
                    )
                    has_business_roles = bool(existing_roles & {"winner", "bidder", "supplier"})
                    if not has_business_roles:
                        related_parts = session.execute(
                            select(EventParticipant).where(
                                EventParticipant.event_id == related.id,
                                EventParticipant.role.in_(["winner", "bidder", "supplier"]),
                            )
                        ).scalars().all()
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

    t03_task = run_single_signal.delay("T03", dry_run=False, force_refresh=True).id
    t05_task = run_single_signal.delay("T05", dry_run=False, force_refresh=True).id
    er_task = run_entity_resolution.delay().id

    result = {
        "status": "dispatched",
        "events_scanned": len(events),
        "catmat_normalized": updated_catmat,
        "catmat_enriched": enriched_catmat,
        "participants_enriched": enriched_participants,
        "tasks": {
            "t03_refresh": t03_task,
            "t05_refresh": t05_task,
            "er_run": er_task,
        },
    }
    log.info("backfill_signal_clarity.done", **result)
    return result


@shared_task(name="worker.tasks.maintenance_tasks.backfill_public_profile_photos")
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
                photo_url = _fetch_camara_photo(deputado_id)
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
