import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from shared.config import settings
from shared.models.orm import Entity, Event, EventParticipant
from shared.models.canonical import CanonicalEntity, CanonicalEvent
from shared.utils.hashing import hash_cpf
from shared.utils.text import normalize_name

# Limits for batch operations:
# asyncpg caps query parameters at 32 767.
# Event table has 9 columns  → max ~3 600 rows/batch; use 3 000.
# EventParticipant has 5 cols → max ~6 500 rows/batch; use 5 000.
# IN clause batching uses the same 5 000 ceiling.
_BATCH_INSERT_EVENTS = 3_000
_BATCH_INSERT_PARTICIPANTS = 5_000
_BATCH_IN_SIZE = 5_000


def _digits_only(value: object) -> str:
    if value is None:
        return ""
    return "".join(ch for ch in str(value) if ch.isdigit())


_MISSING_CLASSIFICATION_VALUES = {
    "",
    "unknown",
    "sem classificacao",
    "sem classificação",
    "null",
    "none",
    "nao_informado",
    "não informado",
}


def _normalize_classification(value: object) -> str:
    text = str(value or "").strip()
    if text.lower() in _MISSING_CLASSIFICATION_VALUES:
        return "nao_informado"
    return text


def _sanitize_event_attrs(attrs: dict | None) -> dict:
    cleaned = dict(attrs or {})

    catmat_group = cleaned.get("catmat_group")
    catmat_code = cleaned.get("catmat_code")
    if catmat_group is not None or catmat_code is not None:
        normalized = _normalize_classification(catmat_group or catmat_code)
        cleaned["catmat_group"] = normalized

    source_pncp_id = str(cleaned.get("source_pncp_id") or "").strip()
    if source_pncp_id:
        cleaned["source_pncp_id"] = source_pncp_id

    return cleaned


def _enrich_event_attrs_from_related_event(
    session: Session,
    attrs: dict,
) -> dict:
    source_pncp_id = str(attrs.get("source_pncp_id") or "").strip()
    if not source_pncp_id:
        return attrs

    needs_catmat = _normalize_classification(attrs.get("catmat_group")) == "nao_informado"
    needs_modality = not str(attrs.get("modality") or "").strip()
    if not needs_catmat and not needs_modality:
        return attrs

    related_stmt = (
        select(Event)
        .where(
            or_(
                Event.source_id == source_pncp_id,
                Event.attrs["source_pncp_id"].as_string() == source_pncp_id,
            )
        )
        .limit(1)
    )
    related = session.execute(related_stmt).scalar_one_or_none()
    if related is None:
        return attrs

    related_attrs = related.attrs or {}
    if needs_catmat:
        attrs["catmat_group"] = _normalize_classification(
            related_attrs.get("catmat_group") or related_attrs.get("catmat_code")
        )
    if needs_modality:
        related_modality = str(related_attrs.get("modality") or "").strip()
        if related_modality:
            attrs["modality"] = related_modality

    return attrs


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
        normalized["cpf"] = cpf
        normalized["cpf_hash"] = hash_cpf(cpf, settings.CPF_HASH_SALT)
    normalized.pop("cpf_masked", None)

    if cnpj_cpf:
        if len(cnpj_cpf) == 14:
            normalized["cnpj"] = cnpj_cpf
        elif len(cnpj_cpf) == 11:
            normalized["cpf"] = cnpj_cpf
            normalized["cpf_hash"] = hash_cpf(cnpj_cpf, settings.CPF_HASH_SALT)
        normalized.pop("cnpj_cpf", None)

    return normalized


def _find_existing_entity_by_strong_identifier(
    session: Session,
    normalized_identifiers: dict,
) -> Entity | None:
    cnpj = _digits_only(normalized_identifiers.get("cnpj"))
    if len(cnpj) == 14:
        stmt = select(Entity).where(Entity.identifiers["cnpj"].as_string() == cnpj)
        entity = session.execute(stmt).scalar_one_or_none()
        if entity:
            return entity

    cpf_hash = str(normalized_identifiers.get("cpf_hash", "")).strip()
    if cpf_hash:
        stmt = select(Entity).where(Entity.identifiers["cpf_hash"].as_string() == cpf_hash)
        entity = session.execute(stmt).scalar_one_or_none()
        if entity:
            return entity

    return None


def batch_prefetch_entities(
    session: Session,
    canonicals: list[CanonicalEntity],
) -> dict[str, Entity]:
    """Bulk-fetch existing entities for a batch of canonical entities.

    Normalizes identifiers for each canonical and executes at most 2 IN queries
    (one for CNPJ, one for cpf_hash) instead of up to 2×N individual SELECTs,
    reducing entity-lookup round trips from O(N log N) to O(log N) per chunk.

    Returns a mutable lookup dict keyed by:
      "cnpj:{14-digit}"  → Entity
      "cpf_hash:{hash}"  → Entity

    Callers should update the dict in-place after creating new entities so that
    subsequent lookups in the same batch resolve without additional DB queries.
    """
    cnpjs: list[str] = []
    cpf_hashes: list[str] = []
    for c in canonicals:
        ids = _normalize_identifiers(c.identifiers)
        cnpj = _digits_only(ids.get("cnpj"))
        if len(cnpj) == 14:
            cnpjs.append(cnpj)
        h = str(ids.get("cpf_hash", "")).strip()
        if h:
            cpf_hashes.append(h)

    lookup: dict[str, Entity] = {}

    unique_cnpjs = list(set(cnpjs))
    for offset in range(0, len(unique_cnpjs), _BATCH_IN_SIZE):
        batch = unique_cnpjs[offset : offset + _BATCH_IN_SIZE]
        rows = session.execute(
            select(Entity).where(Entity.identifiers["cnpj"].as_string().in_(batch))
        ).scalars().all()
        for ent in rows:
            v = _digits_only(ent.identifiers.get("cnpj"))
            if v:
                lookup[f"cnpj:{v}"] = ent

    unique_hashes = list(set(cpf_hashes))
    for offset in range(0, len(unique_hashes), _BATCH_IN_SIZE):
        batch = unique_hashes[offset : offset + _BATCH_IN_SIZE]
        rows = session.execute(
            select(Entity).where(Entity.identifiers["cpf_hash"].as_string().in_(batch))
        ).scalars().all()
        for ent in rows:
            h = str(ent.identifiers.get("cpf_hash", "")).strip()
            if h:
                lookup[f"cpf_hash:{h}"] = ent

    return lookup


def upsert_entity_with_lookup(
    session: Session,
    canonical: CanonicalEntity,
    entity_lookup: dict[str, Entity],
) -> Entity:
    """Upsert an entity using a pre-fetched lookup dict instead of individual SELECTs.

    Updates entity_lookup in-place so subsequent entities with the same
    CNPJ/cpf_hash in the same batch resolve without any additional DB query.
    """
    normalized_identifiers = _normalize_identifiers(canonical.identifiers)
    cnpj = _digits_only(normalized_identifiers.get("cnpj"))
    cpf_hash = str(normalized_identifiers.get("cpf_hash", "")).strip()

    entity: Entity | None = None
    if len(cnpj) == 14:
        entity = entity_lookup.get(f"cnpj:{cnpj}")
    if entity is None and cpf_hash:
        entity = entity_lookup.get(f"cpf_hash:{cpf_hash}")

    if entity:
        entity.attrs = {**entity.attrs, **canonical.attrs}
        entity.identifiers = {**entity.identifiers, **normalized_identifiers}
        if canonical.name and not entity.name:
            entity.name = canonical.name
            entity.name_normalized = normalize_name(canonical.name)
        return entity

    # Fallback: org/company lookup by name (entities without CNPJ/CPF — rare path).
    if canonical.type in {"org", "company"} and canonical.name:
        normalized_name = normalize_name(canonical.name)
        stmt = select(Entity).where(
            Entity.type == canonical.type,
            Entity.name_normalized == normalized_name,
        ).limit(1)
        entity = session.execute(stmt).scalars().first()
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

    # Update lookup so subsequent entities with the same CNPJ/cpf_hash in this
    # batch find the freshly-created entity without a round trip.
    if len(cnpj) == 14:
        entity_lookup[f"cnpj:{cnpj}"] = entity
    if cpf_hash:
        entity_lookup[f"cpf_hash:{cpf_hash}"] = entity

    return entity


def batch_upsert_events(
    session: Session,
    canonicals: list[CanonicalEvent],
) -> dict[tuple[str, str], Event]:
    """Batch INSERT ... ON CONFLICT for a list of events.

    Replaces N individual INSERT round trips with:
      - 1 IN query for PNCP attr enrichment (was 1 SELECT per event)
      - ceil(N / 3000) bulk INSERT ON CONFLICT statements

    Returns a dict keyed by (source_connector, source_id) → Event so callers
    can look up events by their canonical key when building participant rows.
    """
    if not canonicals:
        return {}

    # Sanitize all attrs.
    attrs_list = [_sanitize_event_attrs(c.attrs) for c in canonicals]

    # Batch PNCP enrichment: 1 IN query instead of 1 SELECT per event.
    pncp_ids = [str(a.get("source_pncp_id") or "").strip() for a in attrs_list]
    non_empty_pncp_ids = list({p for p in pncp_ids if p})
    pncp_lookup: dict[str, dict] = {}
    for offset in range(0, len(non_empty_pncp_ids), _BATCH_IN_SIZE):
        batch = non_empty_pncp_ids[offset : offset + _BATCH_IN_SIZE]
        rows = session.execute(
            select(Event).where(
                or_(
                    Event.source_id.in_(batch),
                    Event.attrs["source_pncp_id"].as_string().in_(batch),
                )
            )
        ).scalars().all()
        for row in rows:
            related_attrs = row.attrs or {}
            if row.source_id in non_empty_pncp_ids:
                pncp_lookup.setdefault(row.source_id, related_attrs)
            pid_attr = str(related_attrs.get("source_pncp_id") or "").strip()
            if pid_attr:
                pncp_lookup.setdefault(pid_attr, related_attrs)

    for i, (pncp_id, attrs) in enumerate(zip(pncp_ids, attrs_list)):
        if not pncp_id:
            continue
        related_attrs = pncp_lookup.get(pncp_id)
        if related_attrs is None:
            continue
        if _normalize_classification(attrs.get("catmat_group")) == "nao_informado":
            attrs["catmat_group"] = _normalize_classification(
                related_attrs.get("catmat_group") or related_attrs.get("catmat_code")
            )
        if not str(attrs.get("modality") or "").strip():
            related_modality = str(related_attrs.get("modality") or "").strip()
            if related_modality:
                attrs["modality"] = related_modality

    # Build row dicts for batch INSERT.
    # Deduplicate by (source_connector, source_id): keep last occurrence.
    # PostgreSQL ON CONFLICT DO UPDATE cannot affect the same row twice in one statement.
    seen_keys: dict[tuple[str, str], dict] = {}
    for c, attrs in zip(canonicals, attrs_list):
        seen_keys[(c.source_connector, c.source_id)] = {
            "id": uuid.uuid4(),
            "type": c.type,
            "subtype": c.subtype,
            "description": c.description,
            "occurred_at": c.occurred_at,
            "source_connector": c.source_connector,
            "source_id": c.source_id,
            "value_brl": c.value_brl,
            "attrs": attrs,
        }
    rows_data = list(seen_keys.values())

    # Batch INSERT ON CONFLICT, chunked to stay under the 32 767 param limit.
    event_map: dict[tuple[str, str], Event] = {}
    for offset in range(0, len(rows_data), _BATCH_INSERT_EVENTS):
        batch = rows_data[offset : offset + _BATCH_INSERT_EVENTS]
        insert_stmt = pg_insert(Event).values(batch)
        stmt = insert_stmt.on_conflict_do_update(
            constraint="uq_event_source",
            set_={
                "type": func.coalesce(insert_stmt.excluded.type, Event.type),
                "subtype": func.coalesce(insert_stmt.excluded.subtype, Event.subtype),
                "description": func.coalesce(insert_stmt.excluded.description, Event.description),
                "occurred_at": func.coalesce(insert_stmt.excluded.occurred_at, Event.occurred_at),
                "value_brl": func.coalesce(insert_stmt.excluded.value_brl, Event.value_brl),
                "attrs": Event.attrs.concat(insert_stmt.excluded.attrs),
            },
        ).returning(Event)
        for event in session.execute(stmt).scalars():
            event_map[(event.source_connector, event.source_id)] = event

    return event_map


def batch_upsert_participants(
    session: Session,
    rows: list[tuple[uuid.UUID, uuid.UUID, str, dict | None]],
) -> None:
    """Batch INSERT ... ON CONFLICT for participant rows.

    Replaces N individual INSERT round trips with ceil(N / 5000) bulk INSERT
    statements.  Each row is a (event_id, entity_id, role, attrs) tuple.
    """
    if not rows:
        return

    # Deduplicate by (event_id, entity_id, role): keep last occurrence.
    seen_triplets: dict[tuple, dict] = {}
    for event_id, entity_id, role, attrs in rows:
        seen_triplets[(event_id, entity_id, role)] = {
            "id": uuid.uuid4(),
            "event_id": event_id,
            "entity_id": entity_id,
            "role": role,
            "attrs": attrs or {},
        }
    deduped_rows = list(seen_triplets.values())

    for offset in range(0, len(deduped_rows), _BATCH_INSERT_PARTICIPANTS):
        batch = deduped_rows[offset : offset + _BATCH_INSERT_PARTICIPANTS]
        insert_stmt = pg_insert(EventParticipant).values(batch)
        stmt = insert_stmt.on_conflict_do_update(
            constraint="uq_event_participant_triplet",
            set_={
                "attrs": EventParticipant.attrs.concat(insert_stmt.excluded.attrs),
            },
        )
        session.execute(stmt)


def upsert_entity_sync(session: Session, canonical: CanonicalEntity) -> Entity:
    """Upsert an entity by matching on identifiers (CNPJ/CPF) or exact name."""
    normalized_identifiers = _normalize_identifiers(canonical.identifiers)
    entity = _find_existing_entity_by_strong_identifier(
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
        ).limit(1)
        entity = session.execute(stmt).scalars().first()
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
    # No flush here: entity.id is a Python-generated UUID4 (no server-side default),
    # so the ID is already known. SQLAlchemy autoflush will batch-emit all pending
    # entity INSERTs before the next SELECT/INSERT that needs them — far more
    # efficient than 2000 individual flushes per chunk.
    return entity


def upsert_event_sync(session: Session, canonical: CanonicalEvent) -> Event:
    """Upsert an event using INSERT ... ON CONFLICT on (source_connector, source_id)."""
    event_attrs = _sanitize_event_attrs(canonical.attrs)
    event_attrs = _enrich_event_attrs_from_related_event(session, event_attrs)

    stmt = (
        pg_insert(Event)
        .values(
            id=uuid.uuid4(),
            type=canonical.type,
            subtype=canonical.subtype,
            description=canonical.description,
            occurred_at=canonical.occurred_at,
            source_connector=canonical.source_connector,
            source_id=canonical.source_id,
            value_brl=canonical.value_brl,
            attrs=event_attrs,
        )
        .on_conflict_do_update(
            constraint="uq_event_source",
            set_={
                "type": canonical.type or Event.type,
                "subtype": canonical.subtype or Event.subtype,
                "description": canonical.description or Event.description,
                "occurred_at": canonical.occurred_at or Event.occurred_at,
                "value_brl": canonical.value_brl if canonical.value_brl is not None else Event.value_brl,
                "attrs": Event.attrs.concat(event_attrs),
            },
        )
        .returning(Event)
    )
    result = session.execute(stmt)
    event = result.scalar_one()
    return event


def upsert_participant_sync(
    session: Session,
    event_id: uuid.UUID,
    entity_id: uuid.UUID,
    role: str,
    attrs: dict | None = None,
) -> EventParticipant:
    """Upsert a participant link using INSERT ... ON CONFLICT on (event_id, entity_id, role)."""
    stmt = (
        pg_insert(EventParticipant)
        .values(
            id=uuid.uuid4(),
            event_id=event_id,
            entity_id=entity_id,
            role=role,
            attrs=attrs or {},
        )
        .on_conflict_do_update(
            constraint="uq_event_participant_triplet",
            set_={
                "attrs": EventParticipant.attrs.concat(attrs or {}),
            },
        )
        .returning(EventParticipant)
    )
    result = session.execute(stmt)
    participant = result.scalar_one()
    return participant
