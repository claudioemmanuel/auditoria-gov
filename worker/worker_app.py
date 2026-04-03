from celery import Celery
from celery.signals import worker_process_init
from structlog.contextvars import bind_contextvars, clear_contextvars

from shared.config import settings
from shared.logging import log, setup_logging
from shared.scheduler.schedule import BEAT_SCHEDULE
import shared.middleware.task_metrics  # noqa: F401 — registers Celery signals

app = Celery("auditoria")
setup_logging()

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
    # Keep Celery logs machine-parsable and consistent with structlog JSON output.
    worker_hijack_root_logger=False,
    worker_log_format="%(message)s",
    worker_task_log_format="%(message)s",
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
@worker_process_init.connect(weak=False)
def _reset_sync_engine_after_fork(**kwargs):
    clear_contextvars()
    bind_contextvars(
        service="worker-primary",
        component="celery-worker",
        environment=settings.APP_ENV,
    )
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
    # Reset structlog's cached logger after fork. The parent process
    # caches a bound logger (cache_logger_on_first_use=True) that may
    # hold stale file descriptors in the forked child.  Re-configuring
    # forces fresh logger instances in each worker process.
    try:
        setup_logging()
    except Exception:  # noqa: BLE001
        pass


# ── Cold-start bootstrap ──────────────────────────────────────────────────────
# On fresh deployments, the Beat schedule may not fire for up to 2 hours.
# When the ingest worker starts up and the DB has no completed runs at all,
# dispatch an immediate ingest + reference seed so data populates right away.

@app.on_after_finalize.connect
def _cold_start_bootstrap(sender, **kwargs):
    """Fire initial ingest when first deployed with an empty database."""
    from celery.signals import worker_ready

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
            # ── Auto-recover stale ER state (crash recovery) ──────────
            _recover_stale_er_state()

            with SyncSession() as session:
                # Seed reference data if any required category is missing.
                # Check per-category so newly added categories (e.g. siape_orgao)
                # are seeded even when other categories already exist.
                _REQUIRED_REF_CATEGORIES = {"ibge_municipio", "ibge_uf", "siape_orgao"}
                existing_categories = {
                    row[0]
                    for row in session.execute(
                        select(ReferenceData.category).distinct()
                    ).all()
                }
                missing = _REQUIRED_REF_CATEGORIES - existing_categories
                if missing:
                    app.send_task(
                        "worker.tasks.reference_tasks.seed_reference_data",
                        queue="default",
                    )
                    log.info("cold_start.seed_reference_data", missing_categories=sorted(missing))

                # Check if any ingest run has ever completed.
                completed = session.execute(
                    select(func.count(RawRun.id)).where(RawRun.status == "completed")
                ).scalar_one()
                if completed > 0:
                    return  # Not a cold start — skip ingest bootstrap.

            # Trigger first incremental ingest.
            app.send_task(
                "worker.tasks.ingest_tasks.ingest_all_incremental",
                queue="ingest",
            )
            log.info("cold_start.initial_ingest_dispatched")

        except Exception as exc:  # noqa: BLE001
            log.warning(
                "cold_start.skipped",
                error=str(exc),
                error_type=type(exc).__name__,
            )


def _recover_stale_er_state() -> int:
    """On startup: recover any ERRunState stuck in 'running' due to a worker crash.

    Uses the advisory lock as ground truth: if the lock is acquirable the ER
    worker is dead and the row is safe to mark failed.  Returns 1 if recovered,
    0 if ER is legitimately running or no stale state exists.
    """
    from sqlalchemy import select, text

    from shared.db_sync import SyncSession
    from shared.models.orm import ERRunState

    try:
        with SyncSession() as session:
            stale = session.execute(
                select(ERRunState)
                .where(ERRunState.status == "running")
                .limit(1)
            ).scalar_one_or_none()
            if stale is None:
                return 0
            # Advisory lock is the truth: acquirable → worker is dead
            can_lock = session.execute(
                text("SELECT pg_try_advisory_lock(7349812)")
            ).scalar()
            if can_lock:
                stale.status = "failed"
                session.commit()
                session.execute(text("SELECT pg_advisory_unlock(7349812)"))
                log.warning("startup.er_stale_recovered", er_id=str(stale.id))
                try:
                    from shared.services.infra_alerts import _send_infra_alert
                    _send_infra_alert(
                        "er_stale_recovered",
                        source="startup",
                        er_id=str(stale.id),
                        auto_resolved=True,
                    )
                except Exception:  # noqa: BLE001
                    pass
                return 1
            return 0  # ER still running legitimately
    except Exception as exc:  # noqa: BLE001
        log.warning("startup.er_stale_recovery_failed", error=str(exc))
        return 0


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
            log.info(
                "worker_ready.orphans_recovered recovered_count=%s",
                len(orphans),
            )

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
                    "worker_ready.redispatched connector=%s job=%s cursor=%s",
                    connector,
                    job,
                    cursor[:20] if cursor else None,
                )

    except Exception as exc:  # noqa: BLE001
        log.warning(
            "worker_ready.orphan_recovery_failed error_type=%s error=%s",
            type(exc).__name__,
            str(exc),
        )
