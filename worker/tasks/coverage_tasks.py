from datetime import datetime, timezone

from celery import shared_task
from sqlalchemy import func, select

from shared.connectors import ConnectorRegistry
from shared.connectors.veracity import SOURCE_VERACITY_REGISTRY
from shared.db_sync import SyncSession
from shared.logging import log
from shared.models.orm import CoverageRegistry, IngestState, RawRun


@shared_task(name="worker.tasks.coverage_tasks.update_coverage_registry")
def update_coverage_registry():
    """Update coverage registry with freshness metrics.

    For each connector + job:
    1. Check latest IngestState.last_run_at AND latest successful RawRun.
    2. Use the most recent successful timestamp from either source.
    3. Compute freshness_lag_hours.
    4. Count total raw_source items.
    5. Determine status: ok (<24h), warning (24-48h), stale (>48h), pending (never run).
    6. Upsert CoverageRegistry entry.
    """
    log.info("update_coverage_registry.start", n_connectors=len(ConnectorRegistry))

    updated = 0
    now = datetime.now(timezone.utc)

    with SyncSession() as session:
        for name, cls in ConnectorRegistry.items():
            connector = cls()
            for job in connector.list_jobs():
                # Get IngestState
                stmt = select(IngestState).where(
                    IngestState.connector == name,
                    IngestState.job == job.name,
                )
                ingest_state = session.execute(stmt).scalar_one_or_none()

                # Get latest successful RawRun (completed/done/yielded-with-data)
                # "yielded" runs that fetched items are partial successes — the
                # job will resume automatically, so they count for freshness.
                run_stmt = (
                    select(RawRun)
                    .where(
                        RawRun.connector == name,
                        RawRun.job == job.name,
                        RawRun.status.in_(["completed", "done", "yielded"]),
                    )
                    .order_by(RawRun.finished_at.desc())
                    .limit(1)
                )
                latest_success_run = session.execute(run_stmt).scalar_one_or_none()

                # Count total items normalized across all completed/yielded runs.
                # raw_source is transient (deleted after normalization), so we
                # use the canonical items_normalized from raw_run as ground truth.
                total_items = int(
                    session.execute(
                        select(func.coalesce(func.sum(RawRun.items_normalized), 0)).where(
                            RawRun.connector == name,
                            RawRun.job == job.name,
                            RawRun.status.in_(["completed", "yielded"]),
                        )
                    ).scalar_one()
                )

                # Compute freshness — use the most recent successful timestamp
                ingest_ts = ingest_state.last_run_at if ingest_state else None
                run_ts = latest_success_run.finished_at if latest_success_run else None

                if ingest_ts and run_ts:
                    last_success_at = max(ingest_ts, run_ts)
                else:
                    last_success_at = ingest_ts or run_ts

                if last_success_at is None:
                    if total_items > 0:
                        # Data exists but no timestamp — mark as stale
                        freshness_lag_hours = None
                        status = "warning"
                    else:
                        freshness_lag_hours = None
                        status = "pending"
                else:
                    lag = now - last_success_at
                    freshness_lag_hours = lag.total_seconds() / 3600
                    if freshness_lag_hours < 24:
                        status = "ok"
                    elif freshness_lag_hours < 48:
                        status = "warning"
                    else:
                        status = "stale"

                # Upsert CoverageRegistry
                cov_stmt = select(CoverageRegistry).where(
                    CoverageRegistry.connector == name,
                    CoverageRegistry.job == job.name,
                )
                cov = session.execute(cov_stmt).scalar_one_or_none()

                if cov is None:
                    cov = CoverageRegistry(
                        connector=name,
                        job=job.name,
                        domain=job.domain,
                    )
                    session.add(cov)

                cov.status = status
                cov.last_success_at = last_success_at
                cov.freshness_lag_hours = freshness_lag_hours
                cov.total_items = total_items

                # Veracity scoring from static registry
                profile = SOURCE_VERACITY_REGISTRY.get(f"{name}:{job.name}")
                if profile:
                    cov.veracity_score = profile.composite_score
                    cov.veracity_label = profile.veracity_label
                    cov.domain_tier = profile.domain_tier.value

                updated += 1

        session.commit()

    log.info("update_coverage_registry.done", updated=updated)
    return {"status": "completed", "updated": updated}
