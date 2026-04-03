import random

from billiard.exceptions import SoftTimeLimitExceeded
from celery import shared_task
from sqlalchemy import func, select, text
from sqlalchemy.exc import OperationalError

from openwatch_connectors import get_connector
from openwatch_db.db_sync import SyncSession
from openwatch_utils.logging import log
from openwatch_models.orm import RawRun, RawSource
from openwatch_models.raw import RawItem
from openwatch_db.upsert_sync import (
    batch_prefetch_entities,
    upsert_entity_with_lookup,
    batch_upsert_events,
    batch_upsert_participants,
)

# Process raw items in chunks to cap memory for large runs.
# Larger chunks reduce per-chunk overhead (fewer LIMIT queries, commits, and
# PostgreSQL round trips) at the cost of slightly higher peak memory per worker.
# raw_source reads are mostly physical I/O (36% cache hit rate); larger chunks
# improve sequential read efficiency.
_NORMALIZE_CHUNK_SIZE = 5000


@shared_task(
    name="openwatch_pipelines.normalize_tasks.normalize_run",
    bind=True,
    max_retries=15,
)
def normalize_run(self, run_id: str):
    """Normalize raw items from a completed ingest run.

    1. Load RawRun and its RawSource items (in chunks).
    2. Get the connector instance.
    3. Call connector.normalize(job, raw_items) per chunk.
    4. Upsert entities, events, participants via repo layer.
    5. Mark raw_source items as normalized and clear raw_data.
    6. Update RawRun stats.
    """
    log.info("normalize_run.start", run_id=run_id)

    with SyncSession() as session:
        try:
            raw_run = session.get(RawRun, run_id)
            if raw_run is None:
                log.error("normalize_run.run_not_found", run_id=run_id)
                return {"run_id": run_id, "status": "error", "error": "run not found"}

            connector = get_connector(raw_run.connector)

            # Find the matching JobSpec
            job = None
            for j in connector.list_jobs():
                if j.name == raw_run.job:
                    job = j
                    break
            if job is None:
                log.error("normalize_run.job_not_found", connector=raw_run.connector, job=raw_run.job)
                return {"run_id": run_id, "status": "error", "error": "job not found"}

            # Count first for progress tracking.
            count_stmt = select(func.count()).select_from(RawSource).where(
                RawSource.run_id == raw_run.id,
                RawSource.normalized == False,  # noqa: E712
            )
            total_count = session.execute(count_stmt).scalar_one()

            if total_count == 0:
                log.info("normalize_run.nothing_to_normalize", run_id=run_id)
                return {"run_id": run_id, "status": "nothing_to_normalize"}

            total_entities = 0
            total_events = 0
            total_normalized = 0

            from openwatch_config.settings import settings

            # Paginate with LIMIT on normalized=False — after each commit the marked rows
            # disappear from the filter, so offset=0 always returns the next fresh batch.
            # This avoids server-side cursors (which are transaction-scoped and break on commit).
            while True:
                chunk = session.execute(
                    select(RawSource)
                    .where(
                        RawSource.run_id == raw_run.id,
                        RawSource.normalized == False,  # noqa: E712
                    )
                    .limit(_NORMALIZE_CHUNK_SIZE)
                ).scalars().all()

                if not chunk:
                    break

                raw_items = [
                    RawItem(raw_id=rs.raw_id, data=rs.raw_data)
                    for rs in chunk
                ]

                result = connector.normalize(job, raw_items)

                # Collect every canonical entity referenced in this chunk — both
                # standalone entities and those appearing as event participants.
                all_canonicals = list(result.entities)
                for ce in result.events:
                    for p in ce.participants:
                        all_canonicals.append(p.entity_ref)

                # Batch prefetch: 2 IN queries (CNPJ + cpf_hash) replace up to
                # 2×N individual SELECTs, reducing round trips from O(N) to O(1).
                entity_lookup = batch_prefetch_entities(session, all_canonicals)

                # Upsert entities using the lookup dict (no per-entity SELECTs).
                # Dedup by (source_connector, source_id) so duplicate refs within
                # the same chunk are processed once.
                entity_map: dict[tuple[str, str], object] = {}
                for canonical_entity in all_canonicals:
                    key = (canonical_entity.source_connector, canonical_entity.source_id)
                    if key in entity_map:
                        continue
                    entity_map[key] = upsert_entity_with_lookup(
                        session, canonical_entity, entity_lookup
                    )

                total_entities += len(result.entities)

                entities_to_embed: list[dict] = [
                    {"entity_id": str(e.id), "name_normalized": e.name}
                    for e in entity_map.values()
                    if e.name  # type: ignore[union-attr]
                ]

                # Batch upsert events: ceil(N/3000) INSERT ON CONFLICT queries.
                event_map = batch_upsert_events(session, result.events)
                total_events += len(result.events)

                # Batch upsert participants: ceil(N/5000) INSERT ON CONFLICT queries.
                participant_rows: list[tuple] = []
                for canonical_event in result.events:
                    event = event_map.get(
                        (canonical_event.source_connector, canonical_event.source_id)
                    )
                    if event is None:
                        continue
                    for participant in canonical_event.participants:
                        p_key = (
                            participant.entity_ref.source_connector,
                            participant.entity_ref.source_id,
                        )
                        entity = entity_map.get(p_key)
                        if entity is None:
                            continue
                        participant_rows.append(
                            (event.id, entity.id, participant.role, participant.attrs)  # type: ignore[union-attr]
                        )
                batch_upsert_participants(session, participant_rows)

                # DELETE the chunk rows immediately — data is now safely in entity/event tables.
                # entity_raw_source and event_raw_source rows cascade-delete automatically.
                # Provenance is preserved via raw_run (connector, job, cursor fields).
                # This eliminates the 2-step mark→purge→vacuum cycle that caused disk bloat.
                chunk_ids = [rs.id for rs in chunk]
                session.execute(
                    text("DELETE FROM raw_source WHERE id = ANY(:ids)"),
                    {"ids": chunk_ids},
                )

                total_normalized += len(chunk)
                raw_run.items_normalized = total_normalized
                session.commit()

                # Expire session identity map to release ORM object memory each cycle.
                session.expire_all()

                # Fire-and-forget: embed entity names for semantic ER (non-blocking).
                if settings.LLM_PROVIDER != "none" and entities_to_embed:
                    from openwatch_pipelines.ai_tasks import embed_entities_batch
                    embed_entities_batch.delay(entities_to_embed)

                log.info(
                    "normalize_run.chunk",
                    run_id=run_id,
                    chunk_size=len(chunk),
                    progress=f"{total_normalized}/{total_count}",
                )

            log.info(
                "normalize_run.done",
                run_id=run_id,
                entities=total_entities,
                events=total_events,
                raw_items_normalized=total_normalized,
            )

            # Reclaim disk space from cleared raw_data fields.
            # Uses dedicated 'vacuum' queue with 5-min delay so vacuum tasks
            # don't pile up in 'default' and block critical pipeline tasks.
            if total_normalized > 0:
                from openwatch_pipelines.maintenance_tasks import (
                    purge_normalized_raw_source,
                    vacuum_raw_source,
                )
                # Purge dead rows immediately so they don't accumulate until the nightly run
                purge_normalized_raw_source.apply_async(queue="vacuum", countdown=60)
                # Vacuum after purge to reclaim disk space from deleted rows
                vacuum_raw_source.apply_async(queue="vacuum", countdown=180)

            # ── Reactive pipeline: trigger ER when all ingests are done ────
            if total_normalized > 0:
                _maybe_trigger_er()

            return {
                "run_id": run_id,
                "status": "completed",
                "entities": total_entities,
                "events": total_events,
                "raw_items_normalized": total_normalized,
            }

        except OperationalError as exc:
            # Retryable DB errors: deadlocks (concurrent workers on same index)
            # and connection failures (postgres restart / transient network).
            # The transaction was aborted, so uncommitted chunks are still in
            # raw_source. Invalidate session and retry with jitter.
            session.invalidate()
            orig = getattr(exc, "orig", None)
            pgcode = getattr(orig, "pgcode", None) or getattr(orig, "sqlstate", None)
            is_deadlock = pgcode == "40P01"
            is_connection = "connection" in str(exc).lower()
            if is_deadlock or is_connection:
                countdown = random.uniform(5, 30) if is_connection else random.uniform(2, 15)
                log.warning(
                    "normalize_run.operational_retry",
                    run_id=run_id,
                    reason="deadlock" if is_deadlock else "connection",
                    retry_in=round(countdown, 1),
                    retries=self.request.retries,
                )
                raise self.retry(exc=exc, countdown=countdown)
            raise

        except SoftTimeLimitExceeded:
            # The Celery soft time limit fired mid-query. psycopg's connection is
            # stuck in-progress and cannot be rolled back normally. Invalidate the
            # session so SQLAlchemy's context-manager __exit__ skips the rollback
            # attempt, preventing the secondary OperationalError.
            log.warning(
                "normalize_run.soft_time_limit",
                run_id=run_id,
                msg="task exceeded soft time limit; invalidating connection",
            )
            session.invalidate()
            raise


def _maybe_trigger_er() -> None:
    """Dispatch ER reactively after normalization completes.

    Called after each normalize_run completes. The ER task itself holds
    a pg_try_advisory_lock so concurrent dispatches are safe — the second
    one will return ``status: skipped`` immediately.

    ER is incremental (watermark_at) so it's safe to run while ingest
    continues — it only processes already-normalized entities.
    """
    try:
        from openwatch_pipelines.er_tasks import run_entity_resolution

        run_entity_resolution.apply_async(queue="er", countdown=30)
        log.info("_maybe_trigger_er.dispatched", countdown=30)
    except Exception as exc:
        # Never fail the normalize task because of a trigger error
        log.warning("_maybe_trigger_er.error", error=str(exc))
