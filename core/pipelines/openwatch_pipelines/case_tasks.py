from celery import shared_task

from openwatch_db.db_sync import SyncSession
from openwatch_utils.logging import log
from openwatch_services.case_builder import build_cases_from_signals


def _invalidate_radar_cache() -> None:
    """Flush radar/case/signal cache keys from Redis so the API serves fresh data."""
    try:
        import redis
        from openwatch_config.settings import settings

        r = redis.from_url(settings.REDIS_URL, decode_responses=True, socket_connect_timeout=3)
        for pattern in ("cache:*radar*", "cache:*case*", "cache:*signal*"):
            cursor = 0
            while True:
                cursor, keys = r.scan(cursor, match=pattern, count=200)
                if keys:
                    r.delete(*keys)
                if cursor == 0:
                    break
        r.close()
    except Exception:  # noqa: BLE001
        pass


@shared_task(name="worker.tasks.case_tasks.build_cases")
def build_cases():
    """Build investigation cases from ungrouped risk signals.

    Wraps build_cases_from_signals() as a Celery task so it can run
    on the daily beat schedule after signal detection completes.
    Already idempotent: skips signals linked to existing CaseItems.
    """
    log.info("build_cases.start")

    with SyncSession() as session:
        cases = build_cases_from_signals(session)

    _invalidate_radar_cache()
    log.info("build_cases.done", cases_created=len(cases))
    return {"status": "completed", "cases_created": len(cases)}
