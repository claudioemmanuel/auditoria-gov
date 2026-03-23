import hashlib
import json
import uuid
from datetime import datetime, timezone

from celery import shared_task
from sqlalchemy.dialects.postgresql import insert as pg_insert

from shared.logging import log
from shared.models.orm import SignalEntity, SignalEvent

_COMPLETENESS_THRESHOLD = 0.65


def _compute_dedup_key(
    typology_code: str, entity_ids: list, event_ids: list, period_start, period_end,
) -> str:
    """Deterministic hash for signal deduplication across runs."""
    parts = [
        typology_code,
        ",".join(sorted(str(eid) for eid in entity_ids)),
        ",".join(sorted(str(eid) for eid in event_ids)),
        str(period_start) if period_start else "",
        str(period_end) if period_end else "",
    ]
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode()).hexdigest()


def _compute_completeness(signal) -> tuple[float, str]:
    evidence_refs = list(signal.evidence_refs or [])
    factors = signal.factors or {}

    evidence_score = 0.0
    if evidence_refs:
        count_component = min(len(evidence_refs), 3) / 3
        with_origin = sum(1 for ref in evidence_refs if ref.url or ref.ref_id)
        with_provenance = sum(
            1 for ref in evidence_refs if getattr(ref, "source_hash", None) or getattr(ref, "snapshot_uri", None)
        )
        origin_component = with_origin / len(evidence_refs)
        provenance_component = with_provenance / len(evidence_refs)
        evidence_score = min(1.0, (0.5 * count_component) + (0.3 * origin_component) + (0.2 * provenance_component))

    period_score = 0.0
    if signal.period_start and signal.period_end:
        period_score = 1.0
    elif signal.period_start or signal.period_end:
        period_score = 0.5

    score = (
        0.20 * (1.0 if signal.entity_ids else 0.0)
        + 0.15 * (1.0 if signal.event_ids else 0.0)
        + 0.15 * period_score
        + 0.15 * (1.0 if factors else 0.0)
        + 0.35 * evidence_score
    )
    rounded = round(min(max(score, 0.0), 1.0), 4)
    status = "sufficient" if rounded >= _COMPLETENESS_THRESHOLD else "insufficient"
    return rounded, status


def _compute_evidence_signature(db_signal, evidence_package) -> str:
    payload = {
        "signal": {
            "id": str(db_signal.id),
            "typology_id": str(db_signal.typology_id),
            "severity": db_signal.severity,
            "confidence": db_signal.data_completeness,
            "title": db_signal.title,
            "summary": db_signal.summary,
            "completeness_score": db_signal.completeness_score,
            "completeness_status": db_signal.completeness_status,
            "factors": db_signal.factors or {},
            "evidence_refs": db_signal.evidence_refs or [],
            "entity_ids": db_signal.entity_ids or [],
            "event_ids": db_signal.event_ids or [],
            "period_start": db_signal.period_start.isoformat() if db_signal.period_start else None,
            "period_end": db_signal.period_end.isoformat() if db_signal.period_end else None,
        },
        "evidence_package": {
            "id": str(evidence_package.id),
            "source_url": evidence_package.source_url,
            "source_hash": evidence_package.source_hash,
            "captured_at": evidence_package.captured_at.isoformat() if evidence_package.captured_at else None,
            "parser_version": evidence_package.parser_version,
            "model_version": evidence_package.model_version,
            "raw_snapshot_uri": evidence_package.raw_snapshot_uri,
            "normalized_snapshot_uri": evidence_package.normalized_snapshot_uri,
        },
    }
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


async def _populate_signal_links(session, signal_id, entity_ids, event_ids):
    # Batch insert event links
    event_rows = []
    for eid_str in (event_ids or []):
        try:
            event_rows.append({"signal_id": signal_id, "event_id": uuid.UUID(str(eid_str))})
        except (ValueError, TypeError):
            pass
    if event_rows:
        stmt = pg_insert(SignalEvent).values(event_rows).on_conflict_do_nothing(constraint='uq_signal_event')
        await session.execute(stmt)

    # Batch insert entity links
    entity_rows = []
    for eid_str in (entity_ids or []):
        try:
            entity_rows.append({"signal_id": signal_id, "entity_id": uuid.UUID(str(eid_str))})
        except (ValueError, TypeError):
            pass
    if entity_rows:
        stmt = pg_insert(SignalEntity).values(entity_rows).on_conflict_do_nothing(constraint='uq_signal_entity')
        await session.execute(stmt)


def _should_run_typology(
    typology, last_runs: dict, domain_freshness: dict,
) -> bool:
    """Check if a typology has new data since its last successful run.

    Uses pre-computed domain_freshness map (domain → MAX(event.created_at))
    to avoid per-typology DB queries.
    Returns True if the typology should run (new data exists or never ran).
    """
    last_run = last_runs.get(typology.id)
    if last_run is None or last_run.finished_at is None:
        return True  # Never ran successfully — must run

    domains = typology.required_domains
    if not domains:
        return True  # No domain filter — always run

    # Check if ANY required domain has events newer than last run
    finished = last_run.finished_at
    if finished.tzinfo is None:
        from datetime import timezone
        finished = finished.replace(tzinfo=timezone.utc)

    for domain in domains:
        last_event_at = domain_freshness.get(domain)
        if last_event_at is not None and last_event_at > finished:
            return True

    return False


@shared_task(name="worker.tasks.signal_tasks.run_all_signals", max_retries=1)
def run_all_signals(dry_run: bool = False, force: bool = False):
    """Execute all active typology detectors in dependency order (incremental).

    Skips typologies whose required event domains have no new data since
    the last successful run. Pass force=True to run all regardless.

    Wave 1: Independent typologies (no ER/meta dependency).
    Wave 2: ER-dependent typologies (T13, T17).
    Wave 3: Meta-typology that depends on wave 1+2 results (T14), dispatched with a delay.
    """
    from sqlalchemy import func, select

    from shared.db_sync import SyncSession
    from shared.models.orm import Event, TypologyRunLog
    from shared.typologies.registry import get_all_typologies

    log.info("run_all_signals", dry_run=dry_run, force=force)
    typologies = get_all_typologies()
    log.info("loaded_typologies", count=len(typologies))

    # Pre-fetch all incremental state in ONE session (2-3 queries total
    # instead of 22+ per-typology queries)
    last_runs: dict = {}
    domain_freshness: dict = {}
    if not force:
        with SyncSession() as session:
            # 1. Last successful run per typology code (single query with window function)
            from sqlalchemy import text as sa_text
            rows = session.execute(sa_text("""
                SELECT DISTINCT ON (typology_code)
                    typology_code, finished_at
                FROM typology_run_log
                WHERE status = 'success' AND dry_run = false
                ORDER BY typology_code, finished_at DESC
            """)).fetchall()
            for row in rows:
                last_runs[row.typology_code] = row

            # 2. Domain freshness: MAX(event.created_at) per event type
            # Covers all unique domains across all typologies in one query
            all_domains = set()
            for t in typologies:
                all_domains.update(t.required_domains)
            if all_domains:
                freshness_rows = session.execute(
                    select(Event.type, func.max(Event.created_at))
                    .where(Event.type.in_(list(all_domains)))
                    .group_by(Event.type)
                ).fetchall()
                for row in freshness_rows:
                    ts = row[1]
                    if ts is not None and ts.tzinfo is None:
                        ts = ts.replace(tzinfo=datetime.now(timezone.utc).tzinfo)
                    domain_freshness[row[0]] = ts

        log.info(
            "run_all_signals.incremental_state",
            last_runs=len(last_runs),
            domains_checked=len(domain_freshness),
        )

    # Wave 1: Independent typologies (no ER/meta dependency)
    wave1_codes = {"T01","T02","T03","T04","T05","T06","T07","T08","T09","T10","T11","T12","T15","T16","T18","T19","T20","T21","T22"}
    # Wave 2: ER-dependent
    wave2_codes = {"T13","T17"}
    # Wave 3: Meta-typology (depends on wave 1+2 results)
    wave3_codes = {"T14"}

    wave1 = [t for t in typologies if t.id in wave1_codes]
    wave2 = [t for t in typologies if t.id in wave2_codes]
    wave3 = [t for t in typologies if t.id in wave3_codes]

    dispatched = 0
    skipped = 0

    log.info("run_all_signals.wave1", codes=[t.id for t in wave1])
    for t in wave1:
        if force or _should_run_typology(t, last_runs, domain_freshness):
            run_single_signal.delay(t.id, dry_run=dry_run)
            dispatched += 1
        else:
            skipped += 1
            log.info("run_all_signals.skipped", typology=t.id, reason="no_new_events")

    log.info("run_all_signals.wave2_er_dependent", codes=[t.id for t in wave2])
    for t in wave2:
        if force or _should_run_typology(t, last_runs, domain_freshness):
            run_single_signal.delay(t.id, dry_run=dry_run)
            dispatched += 1
        else:
            skipped += 1
            log.info("run_all_signals.skipped", typology=t.id, reason="no_new_events")

    # Wave 3: Meta-typology — run if any wave 1/2 typology was dispatched
    # (new signals from earlier waves may produce new compound signals)
    log.info("run_all_signals.wave3_meta", codes=[t.id for t in wave3])
    for t in wave3:
        if force or dispatched > 0:
            run_single_signal.apply_async(
                args=[t.id],
                kwargs={"dry_run": dry_run},
                countdown=60,
            )
            dispatched += 1
        else:
            skipped += 1
            log.info("run_all_signals.skipped", typology=t.id, reason="no_new_signals")

    log.info(
        "run_all_signals.dispatch_summary",
        dispatched=dispatched,
        skipped=skipped,
        force=force,
    )

    # ── Reactive pipeline: trigger case building after signals settle ────
    # Only dispatch downstream work if at least one typology was dispatched.
    if not dry_run and dispatched > 0:
        try:
            from worker.tasks.case_tasks import build_cases

            build_cases.apply_async(queue="default", countdown=300)
            log.info("run_all_signals.triggered_cases", countdown=300)
        except Exception as exc:
            log.warning("run_all_signals.trigger_cases_error", error=str(exc))

        # Invalidate radar/signal/case cache entries so the public API
        # serves fresh data after new signals are generated.
        try:
            import redis as redis_lib
            from shared.config import settings as _settings

            r = redis_lib.from_url(_settings.REDIS_URL, socket_connect_timeout=5)
            deleted = 0
            for pattern in ("cache:*radar*", "cache:*case*", "cache:*signal*"):
                cursor = 0
                while True:
                    cursor, keys = r.scan(cursor, match=pattern, count=200)
                    if keys:
                        r.delete(*keys)
                        deleted += len(keys)
                    if cursor == 0:
                        break
            r.close()
            log.info("run_all_signals.cache_invalidated", deleted=deleted)
        except Exception as exc:
            log.warning("run_all_signals.cache_invalidate_error", error=str(exc))
    elif not dry_run and dispatched == 0:
        log.info("run_all_signals.all_skipped", reason="no_new_data")

    return {
        "status": "dispatched" if dispatched > 0 else "skipped",
        "dispatched": dispatched,
        "skipped": skipped,
        "count": len(typologies),
        "dry_run": dry_run,
        "force": force,
        "waves": [len(wave1), len(wave2), len(wave3)],
    }


@shared_task(name="worker.tasks.signal_tasks.run_single_signal", max_retries=2)
def run_single_signal(
    typology_code: str,
    dry_run: bool = False,
    force_refresh: bool = False,
):
    """Execute a single typology detector with dedup and optional dry-run.

    1. Load the typology from registry.
    2. Call typology.run(session).
    3. Compute dedup_key per signal to skip already-stored duplicates.
    4. Upsert resulting RiskSignal records (unless dry_run).
    5. Dispatch AI explanation for HIGH/CRITICAL signals.
    6. Log execution funnel (candidates, deduped, created).
    7. Persist execution metrics into TypologyRunLog.
    """
    from sqlalchemy import select

    from shared.config import settings
    from shared.db import async_session
    from shared.models.orm import EvidencePackage, RiskSignal, Typology, TypologyRunLog
    from shared.typologies.registry import get_typology
    from shared.utils.sync_async import run_async
    from worker.tasks.ai_tasks import explain_pending_signals

    log.info(
        "run_single_signal.start",
        typology=typology_code,
        dry_run=dry_run,
        force_refresh=force_refresh,
    )

    typology = get_typology(typology_code)

    async def _run() -> dict:
        async with async_session() as session:
            # Create run log entry
            run_started = datetime.now(timezone.utc)
            run_log = TypologyRunLog(
                typology_code=typology_code,
                status="running",
                started_at=run_started,
                dry_run=dry_run,
            )
            session.add(run_log)
            await session.flush()

            try:
                # Ensure the typology row exists in the DB
                typ_stmt = select(Typology).where(Typology.code == typology_code)
                typ_row = (await session.execute(typ_stmt)).scalar_one_or_none()

                if typ_row is None:
                    typ_row = Typology(
                        code=typology.id,
                        name=typology.name,
                        description=typology.__class__.__doc__ or "",
                        required_domains=typology.required_domains,
                        active=True,
                    )
                    session.add(typ_row)
                    await session.flush()

                # Run the typology detection
                signals = await typology.run(session)

                candidates = len(signals)
                created = 0
                refreshed = 0
                deduped = 0
                blocked = 0
                has_high_critical = False

                # Pre-compute all dedup keys and batch-check existing signals
                # to avoid N individual DB queries (O(n) → O(1) batch lookup).
                signal_dedup_keys: list[str] = []
                for signal in signals:
                    signal_dedup_keys.append(_compute_dedup_key(
                        typology_code,
                        signal.entity_ids,
                        signal.event_ids,
                        signal.period_start,
                        signal.period_end,
                    ))

                existing_by_dedup: dict[str, object] = {}
                if not dry_run and signal_dedup_keys:
                    _DEDUP_CHUNK = 5_000
                    for _di in range(0, len(signal_dedup_keys), _DEDUP_CHUNK):
                        _dk_batch = signal_dedup_keys[_di : _di + _DEDUP_CHUNK]
                        for _existing in (
                            await session.execute(
                                select(RiskSignal).where(RiskSignal.dedup_key.in_(_dk_batch))
                            )
                        ).scalars().all():
                            existing_by_dedup[_existing.dedup_key] = _existing

                for sig_idx, signal in enumerate(signals):
                    dedup_key = signal_dedup_keys[sig_idx]
                    completeness_score, completeness_status = _compute_completeness(signal)
                    signal_factors = dict(signal.factors or {})
                    stored_severity = signal.severity.value
                    if completeness_status == "insufficient":
                        signal_factors["gated_by_completeness"] = True
                        signal_factors["completeness_threshold"] = _COMPLETENESS_THRESHOLD
                        if stored_severity in ("high", "critical"):
                            stored_severity = "medium"
                            blocked += 1

                    if not dry_run:
                        # Check dedup — skip if signal already exists unless force_refresh=True.
                        # This also catches intra-batch duplicates (same dedup_key
                        # generated multiple times within a single typology run).
                        existing_signal = existing_by_dedup.get(dedup_key)

                        if existing_signal is not None and not force_refresh:
                            deduped += 1
                            continue

                        # Semantic dedup: skip if a very similar signal already exists.
                        if settings.LLM_PROVIDER != "none" and signal.summary:
                            from sqlalchemy import text as _sa_text
                            from shared.ai.provider import get_llm_provider as _get_provider
                            _provider = _get_provider()
                            _emb_result = await _provider.embed([signal.summary])
                            if _emb_result and any(v != 0.0 for v in _emb_result[0]):
                                _vec_str = "[" + ",".join(str(v) for v in _emb_result[0]) + "]"
                                _dup = (await session.execute(
                                    _sa_text("""
                                        SELECT 1 FROM text_embedding te
                                        JOIN text_corpus tc ON tc.id = te.corpus_id
                                        WHERE tc.source_type = 'signal'
                                          AND (te.embedding <=> :q::vector) <= :dist
                                        LIMIT 1
                                    """),
                                    {"q": _vec_str, "dist": 0.10},
                                )).first()
                                if _dup is not None:
                                    deduped += 1
                                    continue

                        source_url = None
                        for ref in signal.evidence_refs:
                            if ref.url:
                                source_url = ref.url
                                break

                        evidence_package = EvidencePackage(
                            source_url=source_url,
                            source_hash=hashlib.sha256(
                                json.dumps(
                                    [ref.model_dump(mode="json") for ref in signal.evidence_refs],
                                    sort_keys=True,
                                    ensure_ascii=False,
                                    default=str,
                                ).encode("utf-8")
                            ).hexdigest()
                            if signal.evidence_refs
                            else None,
                            captured_at=datetime.now(timezone.utc),
                            parser_version=f"typology:{typology_code}",
                            model_version=settings.OPENAI_MODEL,
                            raw_snapshot_uri=f"raw://risk_signal/{dedup_key}",
                            normalized_snapshot_uri=f"signal://risk_signal/{dedup_key}",
                        )
                        session.add(evidence_package)
                        await session.flush()

                        if existing_signal is not None and force_refresh:
                            db_signal = existing_signal
                            db_signal.typology_id = typ_row.id
                            db_signal.severity = stored_severity
                            db_signal.data_completeness = signal.confidence
                            db_signal.title = signal.title
                            db_signal.summary = signal.summary
                            db_signal.completeness_score = completeness_score
                            db_signal.completeness_status = completeness_status
                            db_signal.evidence_package_id = evidence_package.id
                            db_signal.factors = signal_factors
                            db_signal.evidence_refs = [ref.model_dump() for ref in signal.evidence_refs]
                            db_signal.entity_ids = [str(eid) for eid in signal.entity_ids]
                            db_signal.event_ids = [str(eid) for eid in signal.event_ids]
                            db_signal.period_start = signal.period_start
                            db_signal.period_end = signal.period_end
                            db_signal.dedup_key = dedup_key
                            await session.flush()
                            await _populate_signal_links(session, db_signal.id, db_signal.entity_ids, db_signal.event_ids)
                            refreshed += 1
                        else:
                            db_signal = RiskSignal(
                                typology_id=typ_row.id,
                                severity=stored_severity,
                                data_completeness=signal.confidence,
                                title=signal.title,
                                summary=signal.summary,
                                completeness_score=completeness_score,
                                completeness_status=completeness_status,
                                evidence_package_id=evidence_package.id,
                                factors=signal_factors,
                                evidence_refs=[ref.model_dump() for ref in signal.evidence_refs],
                                entity_ids=[str(eid) for eid in signal.entity_ids],
                                event_ids=[str(eid) for eid in signal.event_ids],
                                period_start=signal.period_start,
                                period_end=signal.period_end,
                                dedup_key=dedup_key,
                            )
                            session.add(db_signal)
                            try:
                                async with session.begin_nested():
                                    await session.flush()
                            except Exception as _flush_exc:
                                # Safety net: SAVEPOINT rollback only undoes
                                # this single signal INSERT, not the whole txn.
                                deduped += 1
                                log.warning(
                                    "run_single_signal.intra_batch_dup",
                                    dedup_key=dedup_key,
                                    error=str(_flush_exc)[:200],
                                )
                                continue
                            # Register in cache so later duplicates within
                            # the same batch are caught by the dedup check.
                            existing_by_dedup[dedup_key] = db_signal
                            await _populate_signal_links(session, db_signal.id, db_signal.entity_ids, db_signal.event_ids)
                            created += 1

                            # Embed summary for future semantic dedup checks.
                            if settings.LLM_PROVIDER != "none" and signal.summary:
                                from shared.ai.embeddings import embed_signal_summary
                                try:
                                    await embed_signal_summary(session, db_signal.id, signal.summary)
                                except Exception:
                                    log.warning(
                                        "run_single_signal.embed_failed",
                                        signal_id=str(db_signal.id),
                                    )

                        evidence_package.signature = _compute_evidence_signature(
                            db_signal=db_signal,
                            evidence_package=evidence_package,
                        )

                    if stored_severity in ("high", "critical") and completeness_status == "sufficient":
                        has_high_critical = True

                # Update run log on success
                finished = datetime.now(timezone.utc)
                run_log.status = "success"
                run_log.finished_at = finished
                run_log.duration_ms = int((finished - run_started).total_seconds() * 1000)
                run_log.candidates = candidates
                run_log.signals_created = created
                run_log.signals_deduped = deduped
                run_log.signals_blocked = blocked

                if not dry_run:
                    await session.commit()

                return {
                    "candidates": candidates,
                    "created": created,
                    "refreshed": refreshed,
                    "deduped": deduped,
                    "blocked": blocked,
                    "has_high_critical": has_high_critical,
                }
            except Exception as exc:
                # Update run log on error
                finished = datetime.now(timezone.utc)
                run_log.status = "error"
                run_log.finished_at = finished
                run_log.duration_ms = int((finished - run_started).total_seconds() * 1000)
                run_log.error_message = str(exc)[:4000]
                await session.commit()
                raise

    result = run_async(_run())

    log.info(
        "run_single_signal.done",
        typology=typology_code,
        dry_run=dry_run,
        force_refresh=force_refresh,
        candidates=result["candidates"],
        signals_created=result["created"],
        signals_refreshed=result["refreshed"],
        signals_deduped=result["deduped"],
        signals_blocked=result["blocked"],
    )

    # Dispatch AI explanation for HIGH/CRITICAL signals
    if result["has_high_critical"] and not dry_run:
        explain_pending_signals.delay()

    return {
        "typology": typology_code,
        "dry_run": dry_run,
        "candidates": result["candidates"],
        "signals_created": result["created"],
        "signals_deduped": result["deduped"],
        "signals_blocked": result["blocked"],
    }
