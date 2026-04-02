from celery import shared_task

from openwatch_utils.logging import log


@shared_task(name="worker.tasks.baseline_tasks.compute_all_baselines")
def compute_all_baselines(force: bool = False):
    """Compute baseline distributions (incremental).

    Skips baseline types when no new events exist since last computation.
    Pass force=True to recompute everything regardless.

    1. For each BaselineType:
       a. Check if new events exist since last baseline update (skip if not).
       b. Query relevant events/contracts in the 24-month window.
       c. Group by scope (CATMAT/CATSER code, modality, etc.).
       d. Compute percentile metrics.
       e. If sample < MIN_SAMPLE_SIZE, broaden scope.
       f. Store BaselineSnapshot.
    """
    from openwatch_baselines.compute import compute_all_baselines as _compute
    from openwatch_db.db import async_session
    from openwatch_utils.sync_async import run_async

    log.info("compute_all_baselines.start", force=force)

    async def _run() -> list:
        async with async_session() as session:
            results = await _compute(session, force=force)
            await session.commit()
            return results

    results = run_async(_run())

    log.info("compute_all_baselines.done", baselines_computed=len(results))

    # ── Reactive pipeline: trigger signal detection after baselines ────
    try:
        from openwatch_pipelines.signal_tasks import run_all_signals

        run_all_signals.apply_async(queue="signals", countdown=10)
        log.info("compute_all_baselines.triggered_signals", countdown=10)
    except Exception as exc:
        log.warning("compute_all_baselines.trigger_signals_error", error=str(exc))

    return {"status": "completed", "baselines_computed": len(results)}
