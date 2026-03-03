from datetime import datetime, timezone

import httpx
from celery import shared_task
from sqlalchemy import select

from shared.connectors import get_connector
from shared.db_sync import SyncSession
from shared.logging import log
from shared.models.orm import IngestState, RawRun, RawSource
from shared.models.raw import RawItem
from shared.utils.sync_async import run_async

MAX_PAGES = 10_000  # Effectively unlimited; date range is the real constraint.

# HTTP status codes that should NOT be retried (permanent client errors).
_NON_RETRYABLE_STATUS = frozenset(range(400, 500)) - {408, 429}


def _is_retryable(exc: Exception) -> bool:
    """Return True if the exception is transient and worth retrying."""
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code not in _NON_RETRYABLE_STATUS
    # Timeouts and connection errors are always retryable.
    if isinstance(exc, (httpx.TimeoutException, httpx.ConnectError, ConnectionError, OSError)):
        return True
    return False


def _format_error(exc: Exception) -> str:
    message = str(exc).strip()
    if message:
        return message
    return repr(exc)


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

        try:
            while pages < MAX_PAGES:
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
                    # Preserve cursor even when no items returned (e.g., rate limit
                    # returns empty items with a resume cursor).
                    if next_cursor is not None:
                        current_cursor = next_cursor
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

            # Dispatch normalization if we got data
            if total_items > 0:
                from worker.tasks.normalize_tasks import normalize_run

                normalize_run.delay(str(raw_run.id))

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
    """Trigger ingestion for all enabled BULK (non-incremental) connector jobs."""
    from shared.connectors import ConnectorRegistry

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
