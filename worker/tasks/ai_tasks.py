from celery import shared_task

from shared.logging import log


@shared_task(name="worker.tasks.ai_tasks.explain_pending_signals")
def explain_pending_signals():
    """Generate AI explanations for signals without explanation_md.

    1. Query RiskSignals where explanation_md IS NULL and severity in (HIGH, CRITICAL).
    2. For each signal, call explain_signal() with factors + evidence + RAG context.
    3. Update signal.explanation_md.
    """
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from shared.ai.explain import explain_signal
    from shared.db import async_session
    from shared.models.orm import RiskSignal
    from shared.utils.sync_async import run_async

    log.info("explain_pending_signals.start")

    explained = 0

    async def _run() -> int:
        nonlocal explained
        async with async_session() as session:
            stmt = (
                select(RiskSignal)
                .options(selectinload(RiskSignal.typology))
                .where(
                    RiskSignal.explanation_md.is_(None),
                    RiskSignal.severity.in_(["high", "critical"]),
                )
                .limit(50)
            )
            signals = (await session.execute(stmt)).scalars().all()
            log.info("explain_pending_signals.found", count=len(signals))

            for s in signals:
                try:
                    explanation = await explain_signal(
                        typology_code=s.typology.code,
                        typology_name=s.typology.name,
                        severity=s.severity,
                        confidence=s.confidence,
                        title=s.title,
                        factors=s.factors,
                        evidence_refs=s.evidence_refs,
                        session=session,
                    )
                    s.explanation_md = explanation
                    explained += 1
                except Exception:
                    log.exception(
                        "explain_pending_signals.error",
                        signal_id=str(s.id),
                    )

            await session.commit()
        return explained

    run_async(_run())

    log.info("explain_pending_signals.done", explained=explained)
    return {"status": "completed", "explained": explained}


@shared_task(name="worker.tasks.ai_tasks.classify_texts")
def classify_texts(text_ids: list[str], categories: list[str]):
    """Classify a batch of procurement descriptions.

    1. Load TextCorpus entries by IDs.
    2. Call classify_text() for each.
    3. Store classifications in attrs.
    """
    import uuid

    from sqlalchemy import select

    from shared.ai.classify import classify_text
    from shared.db_sync import SyncSession
    from shared.models.orm import TextCorpus
    from shared.utils.sync_async import run_async

    log.info("classify_texts.start", count=len(text_ids))

    with SyncSession() as session:
        stmt = select(TextCorpus).where(
            TextCorpus.id.in_([uuid.UUID(tid) for tid in text_ids])
        )
        texts = session.execute(stmt).scalars().all()

        classified = 0
        for tc in texts:
            try:
                category = run_async(classify_text(tc.content, categories))
                tc.attrs = {**tc.attrs, "classification": category}
                classified += 1
            except Exception:
                log.exception("classify_texts.error", text_id=str(tc.id))

        session.commit()

    log.info("classify_texts.done", classified=classified)
    return {"status": "completed", "classified": classified}


_PROCUREMENT_CATEGORIES = [
    "obras",
    "servicos",
    "compras",
    "alienacoes",
    "concessoes",
    "outros",
]


@shared_task(name="worker.tasks.ai_tasks.classify_texts_unclassified")
def classify_texts_unclassified():
    """Classify unclassified procurement TextCorpus entries.

    Scheduled daily at 04:45 UTC. Finds entries with source_type='procurement'
    that have no 'classification' in attrs, and classifies up to 200 per run.
    Degrades gracefully when LLM_PROVIDER=none.
    """
    from sqlalchemy import select

    from shared.config import settings
    from shared.db_sync import SyncSession
    from shared.models.orm import TextCorpus

    if settings.LLM_PROVIDER == "none":
        log.info("classify_texts_unclassified.skipped", reason="LLM_PROVIDER=none")
        return {"status": "skipped"}

    from shared.ai.classify import classify_text
    from shared.utils.sync_async import run_async

    log.info("classify_texts_unclassified.start")

    with SyncSession() as session:
        stmt = (
            select(TextCorpus)
            .where(
                TextCorpus.source_type == "procurement",
                TextCorpus.attrs["classification"].as_string().is_(None),
            )
            .limit(200)
        )
        texts = session.execute(stmt).scalars().all()

        log.info("classify_texts_unclassified.found", count=len(texts))

        classified = 0
        for tc in texts:
            try:
                category = run_async(classify_text(tc.content, _PROCUREMENT_CATEGORIES))
                tc.attrs = {**(tc.attrs or {}), "classification": category}
                classified += 1
            except Exception:
                log.exception("classify_texts_unclassified.error", text_id=str(tc.id))

        session.commit()

    log.info("classify_texts_unclassified.done", classified=classified)
    return {"status": "completed", "classified": classified}


@shared_task(name="worker.tasks.ai_tasks.embed_entities_batch")
def embed_entities_batch(entity_items: list):
    """Embed a batch of entity names and store in text_embedding.

    Called from normalize_tasks after each chunk commit.
    Degrades gracefully when LLM_PROVIDER=none (no-op).

    Args:
        entity_items: list of {"entity_id": str, "name_normalized": str}
    """
    from shared.config import settings

    if settings.LLM_PROVIDER == "none":
        return {"status": "skipped"}

    from shared.ai.embeddings import embed_entity
    from shared.db import async_session
    from shared.utils.sync_async import run_async

    log.info("embed_entities_batch.start", count=len(entity_items))

    async def _run() -> int:
        count = 0
        async with async_session() as session:
            for item in entity_items:
                try:
                    await embed_entity(
                        session,
                        item["entity_id"],
                        item["name_normalized"],
                    )
                    count += 1
                except Exception:
                    log.exception(
                        "embed_entities_batch.error",
                        entity_id=item.get("entity_id"),
                    )
            await session.commit()
        return count

    embedded = run_async(_run())
    log.info("embed_entities_batch.done", embedded=embedded)
    return {"status": "completed", "embedded": embedded}
