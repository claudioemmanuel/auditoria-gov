"""One-shot pipeline runner for ECS Scheduled Tasks.

Dispatches the full pipeline (ingest -> normalize -> ER -> baselines ->
signals -> cases -> coverage) and exits when complete.

Usage:
    python -m openwatch_pipelines.run_pipeline [--pipeline full|bulk|signals|maintenance]
"""

import argparse
import logging
import sys
import time

from openwatch_pipelines.worker_app import app

log = logging.getLogger("auditoria.run_pipeline")


def run_full_pipeline() -> None:
    """Dispatch full pipeline and wait for completion."""
    result = app.send_task(
        "openwatch_pipelines.ingest_tasks.ingest_all_incremental",
        queue="ingest",
    )
    log.info("Dispatched ingest_all_incremental: %s", result.id)
    result.get(timeout=7200)
    log.info("Ingest completed. Pipeline chain will follow automatically.")


def run_bulk_pipeline() -> None:
    """Dispatch bulk ingestion (TSE, Receita CNPJ)."""
    result = app.send_task(
        "openwatch_pipelines.ingest_tasks.ingest_all_bulk",
        queue="bulk",
    )
    log.info("Dispatched ingest_all_bulk: %s", result.id)
    result.get(timeout=14400)


def run_signals_pipeline() -> None:
    """Run signals + cases only (assumes data is already ingested)."""
    result = app.send_task(
        "openwatch_pipelines.signal_tasks.run_all_signals",
        queue="signals",
    )
    log.info("Dispatched run_all_signals: %s", result.id)
    result.get(timeout=7200)


def run_maintenance() -> None:
    """Run cleanup and maintenance tasks."""
    for task_name in [
        "openwatch_pipelines.maintenance_tasks.cleanup_stale_runs",
        "openwatch_pipelines.maintenance_tasks.purge_old_results",
        "openwatch_pipelines.maintenance_tasks.purge_normalized_raw_source",
        "openwatch_pipelines.maintenance_tasks.vacuum_raw_source",
    ]:
        result = app.send_task(task_name, queue="default")
        log.info("Dispatched %s: %s", task_name, result.id)
        result.get(timeout=3600)

    result = app.send_task(
        "openwatch_pipelines.coverage_tasks.update_coverage_registry",
        queue="default",
    )
    result.get(timeout=1800)
    log.info("Maintenance complete.")


PIPELINES = {
    "full": run_full_pipeline,
    "bulk": run_bulk_pipeline,
    "signals": run_signals_pipeline,
    "maintenance": run_maintenance,
}


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")

    parser = argparse.ArgumentParser(description="OpenWatch pipeline runner")
    parser.add_argument(
        "--pipeline",
        choices=list(PIPELINES.keys()),
        default="full",
        help="Pipeline to run (default: full)",
    )
    args = parser.parse_args()

    log.info("Starting pipeline: %s", args.pipeline)
    start = time.monotonic()

    try:
        PIPELINES[args.pipeline]()
    except Exception:
        log.exception("Pipeline failed: %s", args.pipeline)
        sys.exit(1)

    elapsed = time.monotonic() - start
    log.info("Pipeline %s completed in %.1f seconds", args.pipeline, elapsed)


if __name__ == "__main__":
    main()
