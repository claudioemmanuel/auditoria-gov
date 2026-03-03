from celery import shared_task

from shared.logging import log


@shared_task(name="worker.tasks.ai_tasks.explain_pending_signals")
def explain_pending_signals():
    """Generate AI explanations for signals without explanation_md.

    1. Query RiskSignals where explanation_md IS NULL and severity in (HIGH, CRITICAL).
    2. For each signal, call explain_signal() with factors + evidence.
    3. Update signal.explanation_md.
    """
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from shared.ai.explain import explain_signal
    from shared.db_sync import SyncSession
    from shared.models.orm import RiskSignal
    from shared.utils.sync_async import run_async

    log.info("explain_pending_signals.start")

    with SyncSession() as session:
        stmt = (
            select(RiskSignal)
            .options(selectinload(RiskSignal.typology))
            .where(
                RiskSignal.explanation_md.is_(None),
                RiskSignal.severity.in_(["high", "critical"]),
            )
            .limit(50)  # Process in batches
        )
        signals = session.execute(stmt).scalars().all()

        log.info("explain_pending_signals.found", count=len(signals))

        explained = 0
        for s in signals:
            try:
                explanation = run_async(
                    explain_signal(
                        typology_code=s.typology.code,
                        typology_name=s.typology.name,
                        severity=s.severity,
                        confidence=s.confidence,
                        title=s.title,
                        factors=s.factors,
                        evidence_refs=s.evidence_refs,
                    )
                )
                s.explanation_md = explanation
                explained += 1
            except Exception:
                log.exception(
                    "explain_pending_signals.error",
                    signal_id=str(s.id),
                )

        session.commit()

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
