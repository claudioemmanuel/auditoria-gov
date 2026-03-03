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
        "worker.tasks.normalize_tasks.*": {"queue": "normalize"},
        "worker.tasks.er_tasks.*": {"queue": "er"},
        "worker.tasks.baseline_tasks.*": {"queue": "default"},
        "worker.tasks.signal_tasks.*": {"queue": "signals"},
        "worker.tasks.ai_tasks.*": {"queue": "ai"},
        "worker.tasks.coverage_tasks.*": {"queue": "default"},
        "worker.tasks.maintenance_tasks.*": {"queue": "default"},
    },
    # ── Performance tuning ───────────────────────────────────────────
    # Fetch one task at a time so long-running ingest doesn't starve
    # other queues when workers share the same process.
    worker_prefetch_multiplier=1,
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
