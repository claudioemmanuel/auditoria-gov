from celery import shared_task
from sqlalchemy import func, select

from shared.connectors import get_connector
from shared.db_sync import SyncSession
from shared.logging import log
from shared.models.orm import RawRun, RawSource
from shared.models.raw import RawItem
from shared.repo.upsert_sync import (
    upsert_entity_sync,
    upsert_event_sync,
    upsert_participant_sync,
)

# Process raw items in chunks to cap memory for large runs.
# Larger chunks reduce per-chunk overhead (fewer LIMIT queries, commits, and
# PostgreSQL round trips) at the cost of slightly higher peak memory per worker.
# raw_source reads are mostly physical I/O (36% cache hit rate); larger chunks
# improve sequential read efficiency.
_NORMALIZE_CHUNK_SIZE = 5000


@shared_task(name="worker.tasks.normalize_tasks.normalize_run")
def normalize_run(run_id: str):
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

        from shared.config import settings

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

            entities_to_embed: list[dict] = []

            # Per-chunk entity identity cache: (source_connector, source_id) → Entity.
            # Eliminates redundant DB lookups when the same entity appears multiple times
            # within one chunk (e.g., candidate with many assets/donations).
            _chunk_entity_cache: dict[tuple[str, str], object] = {}

            def _upsert_entity_cached(canonical_entity):
                key = (canonical_entity.source_connector, canonical_entity.source_id)
                cached = _chunk_entity_cache.get(key)
                if cached is not None:
                    return cached
                entity = upsert_entity_sync(session, canonical_entity)
                _chunk_entity_cache[key] = entity
                return entity

            # Upsert standalone entities
            for canonical_entity in result.entities:
                entity = _upsert_entity_cached(canonical_entity)
                if entity.name:
                    entities_to_embed.append(
                        {"entity_id": str(entity.id), "name_normalized": entity.name}
                    )
                total_entities += 1

            # Upsert events and their participants
            for canonical_event in result.events:
                event = upsert_event_sync(session, canonical_event)
                total_events += 1

                for participant in canonical_event.participants:
                    entity = _upsert_entity_cached(participant.entity_ref)
                    if entity.name:
                        entities_to_embed.append(
                            {"entity_id": str(entity.id), "name_normalized": entity.name}
                        )
                    upsert_participant_sync(
                        session,
                        event_id=event.id,
                        entity_id=entity.id,
                        role=participant.role,
                        attrs=participant.attrs,
                    )

            # Mark chunk as normalized and clear raw_data to free staging space.
            # raw_data is no longer needed once the chunk is in entity/event tables.
            # Commit — next loop iteration re-queries with normalized=False.
            for rs in chunk:
                rs.normalized = True
                rs.raw_data = {}

            total_normalized += len(chunk)
            raw_run.items_normalized = total_normalized
            session.commit()

            # Expire session identity map to release ORM object memory each cycle.
            session.expire_all()

            # Fire-and-forget: embed entity names for semantic ER (non-blocking).
            if settings.LLM_PROVIDER != "none" and entities_to_embed:
                from worker.tasks.ai_tasks import embed_entities_batch
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
            from worker.tasks.maintenance_tasks import vacuum_raw_source
            vacuum_raw_source.apply_async(queue="vacuum", countdown=300)

        return {
            "run_id": run_id,
            "status": "completed",
            "entities": total_entities,
            "events": total_events,
            "raw_items_normalized": total_normalized,
        }
