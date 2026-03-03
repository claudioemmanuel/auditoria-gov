from celery import shared_task
from sqlalchemy import select

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
_NORMALIZE_CHUNK_SIZE = 500


@shared_task(name="worker.tasks.normalize_tasks.normalize_run")
def normalize_run(run_id: str):
    """Normalize raw items from a completed ingest run.

    1. Load RawRun and its RawSource items (in chunks).
    2. Get the connector instance.
    3. Call connector.normalize(job, raw_items) per chunk.
    4. Upsert entities, events, participants via repo layer.
    5. Mark raw_source items as normalized.
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

        # Load un-normalized raw sources
        stmt = select(RawSource).where(
            RawSource.run_id == raw_run.id,
            RawSource.normalized == False,  # noqa: E712
        )
        raw_sources = session.execute(stmt).scalars().all()

        if not raw_sources:
            log.info("normalize_run.nothing_to_normalize", run_id=run_id)
            return {"run_id": run_id, "status": "nothing_to_normalize"}

        total_entities = 0
        total_events = 0
        total_normalized = 0

        from shared.config import settings

        # Process in chunks to avoid memory spikes on large runs.
        for chunk_start in range(0, len(raw_sources), _NORMALIZE_CHUNK_SIZE):
            chunk = raw_sources[chunk_start : chunk_start + _NORMALIZE_CHUNK_SIZE]

            raw_items = [
                RawItem(raw_id=rs.raw_id, data=rs.raw_data)
                for rs in chunk
            ]

            result = connector.normalize(job, raw_items)

            entities_to_embed: list[dict] = []

            # Upsert standalone entities
            for canonical_entity in result.entities:
                entity = upsert_entity_sync(session, canonical_entity)
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
                    entity = upsert_entity_sync(session, participant.entity_ref)
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

            # Mark chunk as normalized
            for rs in chunk:
                rs.normalized = True

            total_normalized += len(chunk)

            # Commit per chunk — releases memory and makes progress visible.
            raw_run.items_normalized = total_normalized
            session.commit()

            # Fire-and-forget: embed entity names for semantic ER (non-blocking).
            if settings.LLM_PROVIDER != "none" and entities_to_embed:
                from worker.tasks.ai_tasks import embed_entities_batch
                embed_entities_batch.delay(entities_to_embed)

            log.info(
                "normalize_run.chunk",
                run_id=run_id,
                chunk_size=len(chunk),
                progress=f"{total_normalized}/{len(raw_sources)}",
            )

        log.info(
            "normalize_run.done",
            run_id=run_id,
            entities=total_entities,
            events=total_events,
            raw_items_normalized=total_normalized,
        )

        return {
            "run_id": run_id,
            "status": "completed",
            "entities": total_entities,
            "events": total_events,
            "raw_items_normalized": total_normalized,
        }
