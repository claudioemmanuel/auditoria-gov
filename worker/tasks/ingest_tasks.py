import os
import time
from datetime import datetime, timezone

import httpx
from celery import shared_task
from sqlalchemy import func, select

from shared.connectors import get_connector
from shared.db_sync import SyncSession
from shared.logging import log
from shared.models.orm import IngestState, RawRun, RawSource
from shared.models.raw import RawItem
from shared.utils.sync_async import run_async

MAX_PAGES = 10_000  # Effectively unlimited; date range is the real constraint.

# ── Time-slice fairness ──────────────────────────────────────────────────────
_MAX_SLICE_SECONDS = int(os.environ.get("INGEST_MAX_SLICE_SECONDS", "1800"))  # 30 min
_STUCK_THRESHOLD_SECONDS = int(os.environ.get("INGEST_STUCK_THRESHOLD_SECONDS", "300"))  # 5 min
_MAX_YIELDS = int(os.environ.get("INGEST_MAX_YIELDS", "20"))  # Max re-enqueues before giving up

# HTTP status codes that should NOT be retried (permanent client errors).
_NON_RETRYABLE_STATUS = frozenset(range(400, 500)) - {408, 429}


def _is_retryable(exc: Exception) -> bool:
    """Return True if the exception is transient and worth retrying."""
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code not in _NON_RETRYABLE_STATUS
    # Timeouts and connection errors are always retryable.
    if isinstance(exc, (httpx.TimeoutException, httpx.ConnectError, ConnectionError, OSError)):
        return True
    # RemoteProtocolError: server dropped connection mid-stream (e.g. TSE CDN cutting large downloads).
    # Retrying restarts the download from scratch, which is correct for idempotent bulk connectors.
    if isinstance(exc, httpx.RemoteProtocolError):
        return True
    return False


def _format_error(exc: Exception) -> str:
    message = str(exc).strip()
    if message:
        return message
    return repr(exc)


def _other_jobs_pending(session, current_connector: str, current_job: str) -> bool:
    """Check if other enabled ingest jobs haven't run recently (>2h) or never ran."""
    from shared.connectors import ConnectorRegistry

    cutoff = datetime.now(timezone.utc)
    for name, cls in ConnectorRegistry.items():
        connector = cls()
        for j in connector.list_jobs():
            if not j.enabled or not j.supports_incremental:
                continue
            if name == current_connector and j.name == current_job:
                continue
            state = session.execute(
                select(IngestState).where(
                    IngestState.connector == name,
                    IngestState.job == j.name,
                )
            ).scalar_one_or_none()
            if state is None or state.last_run_at is None:
                return True  # Never ran
            if (cutoff - state.last_run_at).total_seconds() > 7200:
                return True  # Stale (>2h since last run)
    return False


def _count_recent_yields(session, connector_name: str, job_name: str) -> int:
    """Count consecutive yielded runs for this job (to prevent infinite yield loops)."""
    recent = session.execute(
        select(RawRun.status)
        .where(RawRun.connector == connector_name, RawRun.job == job_name)
        .order_by(RawRun.created_at.desc())
        .limit(_MAX_YIELDS + 1)
    ).scalars().all()
    count = 0
    for s in recent:
        if s == "yielded":
            count += 1
        else:
            break
    return count


def _check_ingest_allowed(session) -> tuple[bool, str]:
    """Return (allowed, reason). Block ingest if disk is low or normalize backlog is too large.

    Hard gates (any one fails → skip ingest):
    - Disk free < 5 GB → refuse immediately (prevents PostgreSQL panic).
    - Unnormalized raw_source rows > 1 M → normalize must drain before more data arrives.
    - Celery 'normalize' queue depth > 500 K → workers are already saturated.
    """
    import shutil
    from sqlalchemy import text

    stat = shutil.disk_usage("/")
    free_gb = stat.free / 1e9
    if free_gb < 5.0:
        return False, f"disk_full: only {free_gb:.1f}GB free (need ≥5GB)"

    backlog = session.execute(
        text("SELECT COUNT(*) FROM raw_source WHERE normalized = false")
    ).scalar()
    if backlog > 1_000_000:
        return False, f"backlog_overloaded: {backlog} unnormalized rows pending (max 1M)"

    # Check Celery queue depth — avoid adding work when workers are already saturated
    try:
        import redis as redis_lib
        from shared.config import settings as _settings
        r = redis_lib.from_url(_settings.REDIS_URL, socket_connect_timeout=2)
        normalize_queue_depth = r.llen("normalize") or 0
        if normalize_queue_depth > 500_000:
            return False, f"queue_saturated: normalize queue has {normalize_queue_depth} pending tasks"
    except Exception:
        pass  # Redis unavailable — fail open

    return True, "ok"


def _finalize_stale_running_runs(session, connector_name: str, job_name: str) -> int:
    """Mark previously running rows as stale before starting a new run.

    This prevents old interrupted rows from appearing permanently "running"
    in monitoring screens after container restarts/crashes.
    """
    stmt = select(RawRun).where(
        RawRun.connector == connector_name,
        RawRun.job == job_name,
        RawRun.status == "running",
        RawRun.finished_at.is_(None),
    )
    stale_runs = session.execute(stmt).scalars().all()
    if not stale_runs:
        return 0

    now = datetime.now(timezone.utc)
    for stale in stale_runs:
        stale.status = "error"
        stale.finished_at = now
        stale.errors = {
            "error": "stale run orphaned by restart/superseded execution",
            "error_type": "StaleRun",
        }

    session.commit()
    log.warning(
        "ingest_connector.stale_runs_closed",
        connector=connector_name,
        job=job_name,
        count=len(stale_runs),
    )
    return len(stale_runs)


@shared_task(
    name="worker.tasks.ingest_tasks.ingest_connector",
    bind=True,
    max_retries=3,
)
def ingest_connector(
    self,
    connector_name: str,
    job_name: str,
    cursor: str | None = None,
    params: dict | None = None,
):
    """Ingest data from a single connector job.

    1. Load IngestState for (connector, job) to get last cursor.
    2. Call connector.fetch(job, cursor) in a loop until no more pages.
    3. Store raw items in raw_source.
    4. Update IngestState with new cursor.
    5. Trigger normalize_run for the new RawRun.
    """
    log.info(
        "ingest_connector.start",
        connector=connector_name,
        job=job_name,
        cursor=cursor,
        has_params=bool(params),
    )

    connector = get_connector(connector_name)

    # Find the matching JobSpec
    job = None
    for j in connector.list_jobs():
        if j.name == job_name:
            job = j
            break
    if job is None:
        log.error("ingest_connector.job_not_found", connector=connector_name, job=job_name)
        return {"connector": connector_name, "job": job_name, "status": "error", "error": "job not found"}

    with SyncSession() as session:
        _finalize_stale_running_runs(session, connector_name, job_name)

        # Hard gate: refuse to start if disk or normalize backlog is overloaded
        allowed, reason = _check_ingest_allowed(session)
        if not allowed:
            log.warning(
                "ingest_connector.skipped",
                connector=connector_name,
                job=job_name,
                reason=reason,
            )
            return {"connector": connector_name, "job": job_name, "status": "skipped", "reason": reason}

        # Load or create IngestState
        stmt = select(IngestState).where(
            IngestState.connector == connector_name,
            IngestState.job == job_name,
        )
        ingest_state = session.execute(stmt).scalar_one_or_none()

        if ingest_state is None:
            ingest_state = IngestState(connector=connector_name, job=job_name)
            session.add(ingest_state)
            session.flush()

        # Use provided cursor, or fall back to last known cursor
        current_cursor = cursor or ingest_state.last_cursor

        # Create RawRun record
        raw_run = RawRun(
            connector=connector_name,
            job=job_name,
            status="running",
            cursor_start=current_cursor,
            items_fetched=0,
        )
        session.add(raw_run)
        session.flush()
        # Persist running state immediately so monitoring endpoints can display in-progress runs.
        session.commit()

        total_items = 0
        pages = 0
        slice_start = time.monotonic()
        last_progress_at = slice_start
        last_progress_count = 0
        yield_count = _count_recent_yields(session, connector_name, job_name)

        try:
            while pages < MAX_PAGES:
                # ── Time-slice check ─────────────────────────────────
                elapsed = time.monotonic() - slice_start
                # Check if yield was requested externally (every 10 pages to avoid DB spam)
                force_yield = False
                if pages % 10 == 0:
                    try:
                        session.refresh(ingest_state, ["yield_requested"])
                        force_yield = ingest_state.yield_requested and current_cursor is not None
                    except Exception:
                        pass  # Column may not exist during rolling deploy
                if (force_yield or elapsed > _MAX_SLICE_SECONDS) and current_cursor is not None:
                    if yield_count >= _MAX_YIELDS and not force_yield:
                        log.warning(
                            "ingest_connector.max_yields_reached",
                            connector=connector_name,
                            job=job_name,
                            yields=yield_count,
                        )
                        # Let it continue — don't yield forever
                    elif force_yield or _other_jobs_pending(session, connector_name, job_name):
                        yield_reason = "force_yield_requested" if force_yield else "time_slice_exceeded"
                        raw_run.items_fetched = total_items
                        raw_run.cursor_end = current_cursor
                        raw_run.status = "yielded"
                        raw_run.finished_at = datetime.now(timezone.utc)
                        raw_run.errors = {
                            "yielded": True,
                            "reason": yield_reason,
                            "elapsed_seconds": int(elapsed),
                            "items_fetched": total_items,
                        }
                        ingest_state.last_cursor = current_cursor
                        ingest_state.last_run_at = datetime.now(timezone.utc)
                        ingest_state.last_run_id = raw_run.id
                        if force_yield:
                            ingest_state.yield_requested = False
                        session.commit()

                        log.info(
                            "ingest_connector.yielded",
                            connector=connector_name,
                            job=job_name,
                            items_fetched=total_items,
                            elapsed_seconds=int(elapsed),
                        )

                        # Dispatch normalization for partial data
                        if total_items > 0:
                            from worker.tasks.normalize_tasks import normalize_run
                            normalize_run.delay(str(raw_run.id))

                        # Re-enqueue at back of queue
                        ingest_connector.apply_async(
                            args=[connector_name, job_name],
                            queue="ingest",
                            countdown=10,
                        )
                        return {
                            "connector": connector_name,
                            "job": job_name,
                            "status": "yielded",
                            "items_fetched": total_items,
                            "cursor": current_cursor,
                        }

                # ── Stuck detection ──────────────────────────────────
                if total_items > last_progress_count:
                    last_progress_at = time.monotonic()
                    last_progress_count = total_items
                elif time.monotonic() - last_progress_at > _STUCK_THRESHOLD_SECONDS and pages > 0:
                    raw_run.status = "error"
                    raw_run.finished_at = datetime.now(timezone.utc)
                    raw_run.errors = {
                        "stuck": True,
                        "reason": f"no_progress_in_{_STUCK_THRESHOLD_SECONDS}s",
                        "items_fetched": total_items,
                        "elapsed_seconds": int(time.monotonic() - slice_start),
                    }
                    ingest_state.last_cursor = current_cursor
                    session.commit()
                    log.warning(
                        "ingest_connector.stuck",
                        connector=connector_name,
                        job=job_name,
                        items_fetched=total_items,
                    )
                    return {
                        "connector": connector_name,
                        "job": job_name,
                        "status": "stuck",
                        "items_fetched": total_items,
                    }

                # ── Fetch next page ──────────────────────────────────
                effective_params = dict(job.default_params or {})
                if params:
                    effective_params.update(params)
                items, next_cursor = run_async(
                    connector.fetch(
                        job,
                        cursor=current_cursor,
                        params=effective_params,
                    )
                )

                if not items:
                    if next_cursor is not None:
                        # Advance through empty windows (e.g., PNCP has no data
                        # for 2021-2022 windows; keep going until real data or end).
                        current_cursor = next_cursor
                        pages += 1  # count against MAX_PAGES to prevent infinite loop
                        continue
                    break

                # Store raw items in bulk (one add_all per page).
                raw_sources = [
                    RawSource(
                        run_id=raw_run.id,
                        connector=connector_name,
                        job=job_name,
                        raw_id=item.raw_id,
                        raw_data=item.data,
                        normalized=False,
                    )
                    for item in items
                ]
                session.add_all(raw_sources)

                total_items += len(items)
                pages += 1
                current_cursor = next_cursor

                raw_run.items_fetched = total_items
                raw_run.cursor_end = current_cursor
                # Save cursor on every page so re-runs resume from here on crash/error.
                ingest_state.last_cursor = current_cursor
                session.commit()

                if pages % 100 == 0 or next_cursor is None:
                    log.info(
                        "ingest_connector.page",
                        connector=connector_name,
                        job=job_name,
                        page=pages,
                        items_in_page=len(items),
                        total=total_items,
                    )

                if next_cursor is None:
                    break

            # Finalize RawRun
            raw_run.items_fetched = total_items
            raw_run.cursor_end = current_cursor
            raw_run.status = "completed"
            raw_run.finished_at = datetime.now(timezone.utc)

            # Update IngestState
            ingest_state.last_cursor = current_cursor
            ingest_state.last_run_at = datetime.now(timezone.utc)
            ingest_state.last_run_id = raw_run.id

            session.commit()

            log.info(
                "ingest_connector.done",
                connector=connector_name,
                job=job_name,
                total_items=total_items,
                pages=pages,
                run_id=str(raw_run.id),
            )

            # Post-run bulk file cleanup (TSE, Receita, etc.)
            if hasattr(connector, "cleanup_bulk_files"):
                try:
                    connector.cleanup_bulk_files(job, raw_run)
                except Exception as _cleanup_exc:
                    log.warning(
                        "ingest.cleanup_bulk_files.failed",
                        connector=connector_name,
                        error=str(_cleanup_exc),
                    )

            # Dispatch normalization if we got data
            if total_items > 0:
                from worker.tasks.normalize_tasks import normalize_run

                normalize_run.delay(str(raw_run.id))

                # Auto-trigger recompute after full ingestion of heavy jobs
                if next_cursor is None and connector_name in {
                    "portal_transparencia",
                    "senado",
                    "camara",
                    "pncp",
                    "comprasnet_contratos",
                    "compras_gov",
                }:
                    from worker.tasks.maintenance_tasks import trigger_post_ingest_recompute
                    trigger_post_ingest_recompute.apply_async(
                        kwargs={"connector": connector_name, "job": job_name},
                        countdown=120,  # 2-minute delay to let normalization start
                        queue="default",
                    )
                    log.info(
                        "ingest_connector.post_ingest_recompute_scheduled",
                        connector=connector_name,
                        job=job_name,
                        countdown=120,
                    )

            return {
                "connector": connector_name,
                "job": job_name,
                "status": "completed",
                "items_fetched": total_items,
                "pages": pages,
                "run_id": str(raw_run.id),
            }

        except Exception as exc:
            formatted_error = _format_error(exc)
            retryable = _is_retryable(exc)
            # Save cursor at the point of failure so the next run resumes from here,
            # not from the beginning. Prevents re-fetching millions of already-stored rows.
            ingest_state.last_cursor = current_cursor
            ingest_state.last_run_at = datetime.now(timezone.utc)
            ingest_state.last_run_id = raw_run.id
            if isinstance(exc, NotImplementedError):
                raw_run.status = "skipped"
                raw_run.errors = {
                    "error": formatted_error,
                    "error_type": type(exc).__name__,
                    "retryable": False,
                }
                raw_run.finished_at = datetime.now(timezone.utc)
                session.commit()
                log.warning(
                    "ingest_connector.skipped",
                    connector=connector_name,
                    job=job_name,
                    reason=formatted_error,
                )
                return {
                    "connector": connector_name,
                    "job": job_name,
                    "status": "skipped",
                    "error": formatted_error,
                }

            # Retryable error with partial data already stored: close the current
            # run as "completed" so normalize can process what was collected, then
            # retry from the saved cursor to fetch the remaining pages.
            if retryable and total_items > 0:
                raw_run.status = "completed"
                raw_run.errors = {
                    "error": formatted_error,
                    "error_type": type(exc).__name__,
                    "retryable": True,
                    "partial": True,
                }
                raw_run.finished_at = datetime.now(timezone.utc)
                session.commit()
                log.warning(
                    "ingest_connector.partial_completed",
                    connector=connector_name,
                    job=job_name,
                    items_fetched=total_items,
                    error=formatted_error,
                )
                from worker.tasks.normalize_tasks import normalize_run
                normalize_run.delay(str(raw_run.id))
                backoff = 60 * (2 ** self.request.retries)
                raise self.retry(exc=exc, countdown=backoff)

            raw_run.status = "error"
            raw_run.errors = {
                "error": formatted_error,
                "error_type": type(exc).__name__,
                "retryable": retryable,
            }
            raw_run.finished_at = datetime.now(timezone.utc)
            session.commit()

            log.error(
                "ingest_connector.error",
                connector=connector_name,
                job=job_name,
                error=formatted_error,
                error_type=type(exc).__name__,
                retryable=retryable,
            )

            if retryable:
                backoff = 60 * (2 ** self.request.retries)  # 60s, 120s, 240s
                raise self.retry(exc=exc, countdown=backoff)
            # Non-retryable (4xx permanent): fail immediately, don't waste retries.
            return {
                "connector": connector_name,
                "job": job_name,
                "status": "error",
                "error": formatted_error,
                "retryable": False,
            }


@shared_task(name="worker.tasks.ingest_tasks.ingest_all_incremental")
def ingest_all_incremental():
    """Trigger ingestion for all enabled connector jobs."""
    from shared.connectors import ConnectorRegistry

    log.info("ingest_all_incremental", n_connectors=len(ConnectorRegistry))

    dispatched = 0
    for name, cls in ConnectorRegistry.items():
        connector = cls()
        for job in connector.list_jobs():
            if job.enabled and job.supports_incremental:
                ingest_connector.delay(name, job.name)
                dispatched += 1

    log.info("ingest_all_incremental.dispatched", count=dispatched)
    return {"status": "dispatched", "count": dispatched}


@shared_task(name="worker.tasks.ingest_tasks.ingest_all_bulk")
def ingest_all_bulk():
    """Trigger ingestion for all enabled BULK (non-incremental) connector jobs.

    Skips dispatch when the disk:throttle Redis flag is set (disk >= 90% full).
    """
    import shutil

    from shared.connectors import ConnectorRegistry

    # Pre-flight disk check: refuse to start bulk jobs if disk is near capacity.
    stat = shutil.disk_usage("/")
    pct_used = (stat.used / stat.total) * 100
    if pct_used >= 90:
        log.warning(
            "ingest_all_bulk.throttled_disk",
            pct_used=round(pct_used, 1),
            free_gb=round(stat.free / 1e9, 2),
        )
        return {"status": "throttled", "reason": "disk_space", "pct_used": round(pct_used, 1)}

    # Also check Redis flag set by disk_space_watchdog.
    try:
        import redis as redis_lib
        from shared.config import settings
        r = redis_lib.from_url(settings.REDIS_URL, socket_connect_timeout=5)
        if r.get("disk:throttle"):
            log.warning("ingest_all_bulk.throttled_disk_flag")
            return {"status": "throttled", "reason": "disk_throttle_flag"}
    except Exception as exc:  # noqa: BLE001
        log.warning("ingest_all_bulk.redis_check_failed", error=str(exc))

    log.info("ingest_all_bulk.start")
    dispatched = 0
    for name, cls in ConnectorRegistry.items():
        connector = cls()
        for job in connector.list_jobs():
            if job.enabled and not job.supports_incremental:
                ingest_connector.apply_async(
                    args=[name, job.name],
                    queue="bulk",
                )
                dispatched += 1
    log.info("ingest_all_bulk.dispatched", count=dispatched)
    return {"status": "dispatched", "count": dispatched}
