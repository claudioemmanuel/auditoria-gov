from celery import shared_task

from shared.db_sync import SyncSession
from shared.logging import log
from shared.services.case_builder import build_cases_from_signals


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

    log.info("build_cases.done", cases_created=len(cases))
    return {"status": "completed", "cases_created": len(cases)}
