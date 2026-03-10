from celery import Celery

from shared.config import settings
from shared.scheduler.schedule import BEAT_SCHEDULE
import shared.middleware.task_metrics  # noqa: F401 — registers Celery signals

app = Celery("auditoria")

app.conf.update(
    broker_url=settings.CELERY_BROKER_URL,
    result_backend=settings.CELERY_RESULT_BACKEND,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="America/Sao_Paulo",
    enable_utc=True,
    beat_schedule=BEAT_SCHEDULE,
    task_routes={
        "worker.tasks.ingest_tasks.*": {"queue": "ingest"},
        "worker.tasks.ingest_tasks.ingest_all_bulk": {"queue": "bulk"},
        "worker.tasks.normalize_tasks.*": {"queue": "normalize"},
        "worker.tasks.er_tasks.*": {"queue": "er"},
        "worker.tasks.baseline_tasks.*": {"queue": "default"},
        "worker.tasks.signal_tasks.*": {"queue": "signals"},
        "worker.tasks.ai_tasks.*": {"queue": "ai"},
        "worker.tasks.coverage_tasks.*": {"queue": "default"},
        "worker.tasks.maintenance_tasks.*": {"queue": "default"},
        "worker.tasks.reference_tasks.*": {"queue": "default"},
        "worker.tasks.case_tasks.*": {"queue": "default"},
    },
    # ── Performance tuning ───────────────────────────────────────────
    # Fetch one task at a time so long-running ingest doesn't starve
    # other queues when workers share the same process.
    worker_prefetch_multiplier=1,
    task_track_started=True,
    # Don't store results for fire-and-forget tasks (ingest, normalize, ER).
    task_ignore_result=False,
    # Auto-expire results after 1 hour to avoid Redis bloat.
    result_expires=3600,
    # Late ack: task is only acked after it finishes, preventing data
    # loss on worker crash mid-execution.
    task_acks_late=True,
    # Reject tasks back to the queue on worker shutdown instead of losing them.
    worker_cancel_long_running_tasks_on_connection_loss=True,
    # Per-task time limits (overridable per @shared_task decorator).
    task_soft_time_limit=3600,  # 60 min soft (large date ranges)
    task_time_limit=3900,       # 65 min hard kill
    # Recycle worker after 100 tasks to release leaked memory.
    worker_max_tasks_per_child=100,
    # ── Dead-letter handling ─────────────────────────────────────────
    # After max_retries exhausted, route to dead-letter queue instead
    # of silently dropping the task.
    task_reject_on_worker_lost=True,
)

app.autodiscover_tasks(["worker.tasks"])


# ── Post-fork engine reset ─────────────────────────────────────────────────────
# Celery uses prefork: each worker child inherits the parent's SQLAlchemy
# connection pool. After fork, psycopg3 connections become invalid/stale.
# Disposing the engine forces each child to open fresh connections on first use.
from celery.signals import worker_process_init  # noqa: E402

@worker_process_init.connect(weak=False)
def _reset_sync_engine_after_fork(**kwargs):
    try:
        from shared.db_sync import sync_engine
        sync_engine.dispose()
    except Exception:  # noqa: BLE001
        pass
    try:
        from shared.db import engine as async_engine
        async_engine.sync_engine.dispose()
    except Exception:  # noqa: BLE001
        pass


# ── Cold-start bootstrap ──────────────────────────────────────────────────────
# On fresh deployments, the Beat schedule may not fire for up to 2 hours.
# When the ingest worker starts up and the DB has no completed runs at all,
# dispatch an immediate ingest + reference seed so data populates right away.

@app.on_after_finalize.connect
def _cold_start_bootstrap(sender, **kwargs):
    """Fire initial ingest when first deployed with an empty database."""
    import logging

    from celery.signals import worker_ready

    log = logging.getLogger("auditoria.cold_start")

    @worker_ready.connect(weak=False)
    def _on_worker_ready(sender, **kw):
        # Only fire from the ingest worker to avoid N parallel bootstraps.
        hostname: str = getattr(sender, "hostname", "") or ""
        if "worker-ingest" not in hostname and "worker-primary" not in hostname:
            return

        try:
            from sqlalchemy import func, select

            from shared.db_sync import SyncSession
            from shared.models.orm import IngestState, RawRun, ReferenceData

            # ── Auto-recover orphaned runs after restart ──────────────
            _recover_orphaned_runs(log, select, SyncSession, RawRun, IngestState)

            with SyncSession() as session:
                # Check if any ingest run has ever completed.
                completed = session.execute(
                    select(func.count(RawRun.id)).where(RawRun.status == "completed")
                ).scalar_one()
                if completed > 0:
                    return  # Not a cold start — skip.

                # Seed reference data first (ibge_municipio, siape_orgao, etc.)
                ref_count = session.execute(
                    select(func.count(ReferenceData.id))
                ).scalar_one()
                if ref_count == 0:
                    app.send_task(
                        "worker.tasks.reference_tasks.seed_reference_data",
                        queue="default",
                    )
                    log.info("cold_start: seeding reference data")

            # Trigger first incremental ingest.
            app.send_task(
                "worker.tasks.ingest_tasks.ingest_all_incremental",
                queue="ingest",
            )
            log.info("cold_start: dispatched initial ingest_all_incremental")

        except Exception as exc:  # noqa: BLE001
            log.warning("cold_start: skipped due to error: %s", exc)


def _recover_orphaned_runs(log, select, SyncSession, RawRun, IngestState):
    """Finalize orphaned 'running' runs and re-dispatch them with saved cursors."""
    from datetime import datetime, timezone

    MAX_REDISPATCH = 4

    try:
        with SyncSession() as session:
            orphans = session.execute(
                select(RawRun).where(
                    RawRun.status == "running",
                    RawRun.finished_at.is_(None),
                )
            ).scalars().all()

            if not orphans:
                return

            now = datetime.now(timezone.utc)
            redispatch_keys: list[tuple[str, str]] = []
            for run in orphans:
                run.status = "error"
                run.finished_at = now
                run.errors = {
                    "error": "stale run orphaned by restart/superseded execution",
                    "error_type": "StaleRun",
                    "auto_recovered": True,
                }
                redispatch_keys.append((run.connector, run.job))

            session.commit()
            log.info("worker_ready: recovered %d orphaned runs", len(orphans))

            # De-duplicate and re-dispatch up to MAX_REDISPATCH
            seen: set[tuple[str, str]] = set()
            dispatched = 0
            for connector, job in redispatch_keys:
                key = (connector, job)
                if key in seen or dispatched >= MAX_REDISPATCH:
                    continue
                seen.add(key)

                state = session.execute(
                    select(IngestState).where(
                        IngestState.connector == connector,
                        IngestState.job == job,
                    )
                ).scalar_one_or_none()
                cursor = state.last_cursor if state else None

                app.send_task(
                    "worker.tasks.ingest_tasks.ingest_connector",
                    args=[connector, job, cursor],
                    queue="ingest",
                    countdown=5,
                )
                dispatched += 1
                log.info(
                    "worker_ready: re-dispatched %s/%s (cursor=%s)",
                    connector, job, cursor[:20] if cursor else None,
                )

    except Exception as exc:  # noqa: BLE001
        log.warning("worker_ready: orphan recovery failed: %s", exc)
