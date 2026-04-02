import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from openwatch_models.orm import EntityRawSource, EventRawSource, RawSource


async def get_raw_sources_for_event(session: AsyncSession, event_id: uuid.UUID) -> list[RawSource]:
    stmt = (
        select(RawSource)
        .join(EventRawSource, EventRawSource.raw_source_id == RawSource.id)
        .where(EventRawSource.event_id == event_id)
    )
    return list((await session.execute(stmt)).scalars().all())


async def get_raw_sources_for_events(
    session: AsyncSession, event_ids: list[uuid.UUID],
) -> dict[uuid.UUID, list[RawSource]]:
    if not event_ids:
        return {}
    stmt = (
        select(EventRawSource.event_id, RawSource)
        .join(RawSource, EventRawSource.raw_source_id == RawSource.id)
        .where(EventRawSource.event_id.in_(event_ids))
    )
    result = await session.execute(stmt)
    mapping: dict[uuid.UUID, list[RawSource]] = {}
    for event_id, raw_source in result:
        mapping.setdefault(event_id, []).append(raw_source)
    return mapping


async def get_raw_sources_for_entity(
    session: AsyncSession, entity_id: uuid.UUID,
) -> list[RawSource]:
    stmt = (
        select(RawSource)
        .join(EntityRawSource, EntityRawSource.raw_source_id == RawSource.id)
        .where(EntityRawSource.entity_id == entity_id)
    )
    return list((await session.execute(stmt)).scalars().all())


async def get_case_provenance_web(
    session: AsyncSession, case_id: uuid.UUID,
) -> dict | None:
    from openwatch_models.orm import Case, CaseItem, RiskSignal

    case_stmt = select(Case).where(Case.id == case_id)
    case = (await session.execute(case_stmt)).scalar_one_or_none()
    if case is None:
        return None

    items_stmt = select(CaseItem).where(CaseItem.case_id == case_id)
    items = list((await session.execute(items_stmt)).scalars().all())
    signal_ids = [item.signal_id for item in items]
    if not signal_ids:
        return {
            "case_id": case.id, "case_title": case.title,
            "signals": [], "event_raw_sources": {},
        }

    signals_stmt = select(RiskSignal).where(RiskSignal.id.in_(signal_ids))
    signals = list((await session.execute(signals_stmt)).scalars().all())

    all_event_ids: set[uuid.UUID] = set()
    for s in signals:
        for eid in (s.event_ids or []):
            try:
                all_event_ids.add(uuid.UUID(str(eid)))
            except (ValueError, TypeError):
                pass

    event_raw_sources = await get_raw_sources_for_events(session, list(all_event_ids))

    return {
        "case_id": case.id,
        "case_title": case.title,
        "signals": [
            {"id": s.id, "title": s.title, "event_ids": s.event_ids or []}
            for s in signals
        ],
        "event_raw_sources": {
            str(eid): [
                {"id": rs.id, "connector": rs.connector, "raw_id": rs.raw_id}
                for rs in sources
            ]
            for eid, sources in event_raw_sources.items()
        },
    }
