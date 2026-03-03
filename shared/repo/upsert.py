import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.config import settings
from shared.models.orm import Entity, Event, EventParticipant, GraphEdge, GraphNode
from shared.models.canonical import CanonicalEntity, CanonicalEvent, CanonicalEdge
from shared.utils.hashing import hash_cpf, mask_cpf
from shared.utils.text import normalize_name


def _digits_only(value: object) -> str:
    if value is None:
        return ""
    return "".join(ch for ch in str(value) if ch.isdigit())


def _normalize_identifiers(identifiers: dict) -> dict:
    normalized = dict(identifiers or {})

    cnpj = _digits_only(normalized.get("cnpj"))
    cpf = _digits_only(normalized.get("cpf"))
    cnpj_cpf = _digits_only(normalized.get("cnpj_cpf"))

    if len(cnpj) == 14:
        normalized["cnpj"] = cnpj
    elif cnpj:
        normalized["cnpj"] = cnpj

    if len(cpf) == 11:
        normalized["cpf_hash"] = hash_cpf(cpf, settings.CPF_HASH_SALT)
        normalized["cpf_masked"] = mask_cpf(cpf)
    normalized.pop("cpf", None)

    if cnpj_cpf:
        if len(cnpj_cpf) == 14:
            normalized["cnpj"] = cnpj_cpf
        elif len(cnpj_cpf) == 11:
            normalized["cpf_hash"] = hash_cpf(cnpj_cpf, settings.CPF_HASH_SALT)
            normalized["cpf_masked"] = mask_cpf(cnpj_cpf)
        normalized.pop("cnpj_cpf", None)

    return normalized


async def _find_existing_entity_by_strong_identifier(
    session: AsyncSession,
    normalized_identifiers: dict,
) -> Entity | None:
    cnpj = _digits_only(normalized_identifiers.get("cnpj"))
    if len(cnpj) == 14:
        stmt = select(Entity).where(Entity.identifiers["cnpj"].as_string() == cnpj)
        result = await session.execute(stmt)
        entity = result.scalar_one_or_none()
        if entity:
            return entity

    cpf_hash = str(normalized_identifiers.get("cpf_hash", "")).strip()
    if cpf_hash:
        stmt = select(Entity).where(Entity.identifiers["cpf_hash"].as_string() == cpf_hash)
        result = await session.execute(stmt)
        entity = result.scalar_one_or_none()
        if entity:
            return entity

    return None


async def upsert_entity(
    session: AsyncSession, canonical: CanonicalEntity
) -> Entity:
    """Upsert an entity by matching on identifiers (CNPJ/CPF) or exact name."""
    normalized_identifiers = _normalize_identifiers(canonical.identifiers)
    entity = await _find_existing_entity_by_strong_identifier(
        session=session,
        normalized_identifiers=normalized_identifiers,
    )
    if entity:
        entity.attrs = {**entity.attrs, **canonical.attrs}
        entity.identifiers = {**entity.identifiers, **normalized_identifiers}
        if canonical.name and not entity.name:
            entity.name = canonical.name
            entity.name_normalized = normalize_name(canonical.name)
        return entity

    # Fallback for non-person entities that frequently lack document IDs (e.g., orgs/UASG).
    if canonical.type in {"org", "company"} and canonical.name:
        normalized_name = normalize_name(canonical.name)
        stmt = select(Entity).where(
            Entity.type == canonical.type,
            Entity.name_normalized == normalized_name,
        )
        result = await session.execute(stmt)
        entity = result.scalar_one_or_none()
        if entity:
            entity.attrs = {**entity.attrs, **canonical.attrs}
            entity.identifiers = {**entity.identifiers, **normalized_identifiers}
            return entity

    entity = Entity(
        type=canonical.type,
        name=canonical.name,
        name_normalized=normalize_name(canonical.name),
        identifiers=normalized_identifiers,
        attrs=canonical.attrs,
    )
    session.add(entity)
    await session.flush()
    return entity


async def upsert_event(
    session: AsyncSession, canonical: CanonicalEvent
) -> Event:
    """Upsert an event by source_connector + source_id."""
    stmt = select(Event).where(
        Event.source_connector == canonical.source_connector,
        Event.source_id == canonical.source_id,
    )
    result = await session.execute(stmt)
    event = result.scalar_one_or_none()

    if event:
        if canonical.type:
            event.type = canonical.type
        if canonical.subtype:
            event.subtype = canonical.subtype
        if canonical.description:
            event.description = canonical.description
        if canonical.occurred_at:
            event.occurred_at = canonical.occurred_at
        if canonical.value_brl is not None:
            event.value_brl = canonical.value_brl
        event.attrs = {**event.attrs, **canonical.attrs}
        return event

    event = Event(
        type=canonical.type,
        subtype=canonical.subtype,
        description=canonical.description,
        occurred_at=canonical.occurred_at,
        source_connector=canonical.source_connector,
        source_id=canonical.source_id,
        value_brl=canonical.value_brl,
        attrs=canonical.attrs,
    )
    session.add(event)
    await session.flush()
    return event


async def upsert_participant(
    session: AsyncSession,
    event_id: uuid.UUID,
    entity_id: uuid.UUID,
    role: str,
    attrs: dict | None = None,
) -> EventParticipant:
    """Upsert a participant link."""
    stmt = select(EventParticipant).where(
        EventParticipant.event_id == event_id,
        EventParticipant.entity_id == entity_id,
        EventParticipant.role == role,
    )
    result = await session.execute(stmt)
    participant = result.scalar_one_or_none()

    if participant:
        if attrs:
            participant.attrs = {**participant.attrs, **attrs}
        return participant

    participant = EventParticipant(
        event_id=event_id,
        entity_id=entity_id,
        role=role,
        attrs=attrs or {},
    )
    session.add(participant)
    await session.flush()
    return participant


async def upsert_edge(
    session: AsyncSession,
    from_node_id: uuid.UUID,
    to_node_id: uuid.UUID,
    edge_type: str,
    weight: float = 1.0,
    attrs: dict | None = None,
) -> GraphEdge:
    """Upsert a graph edge."""
    stmt = select(GraphEdge).where(
        GraphEdge.from_node_id == from_node_id,
        GraphEdge.to_node_id == to_node_id,
        GraphEdge.type == edge_type,
    )
    result = await session.execute(stmt)
    edge = result.scalar_one_or_none()

    if edge:
        edge.weight = weight
        if attrs:
            edge.attrs = {**edge.attrs, **attrs}
        return edge

    edge = GraphEdge(
        from_node_id=from_node_id,
        to_node_id=to_node_id,
        type=edge_type,
        weight=weight,
        attrs=attrs or {},
    )
    session.add(edge)
    await session.flush()
    return edge
