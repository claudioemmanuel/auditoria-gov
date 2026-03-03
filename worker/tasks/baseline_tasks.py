from celery import shared_task

from shared.logging import log


@shared_task(name="worker.tasks.baseline_tasks.compute_all_baselines")
def compute_all_baselines():
    """Compute all baseline distributions.

    1. For each BaselineType:
       a. Query relevant events/contracts in the 24-month window.
       b. Group by scope (CATMAT/CATSER code, modality, etc.).
       c. Compute percentile metrics.
       d. If sample < MIN_SAMPLE_SIZE, broaden scope.
       e. Store BaselineSnapshot.
    """
    from shared.baselines.compute import compute_all_baselines as _compute
    from shared.db import async_session
    from shared.utils.sync_async import run_async

    log.info("compute_all_baselines.start")

    async def _run() -> list:
        async with async_session() as session:
            results = await _compute(session)
            await session.commit()
            return results

    results = run_async(_run())

    log.info("compute_all_baselines.done", baselines_computed=len(results))
    return {"status": "completed", "baselines_computed": len(results)}
