import uuid

from sqlalchemy import or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from shared.config import settings
from shared.models.orm import Entity, Event, EventParticipant
from shared.models.canonical import CanonicalEntity, CanonicalEvent
from shared.utils.hashing import hash_cpf, mask_cpf
from shared.utils.text import normalize_name


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
        )
        entity = session.execute(stmt).scalar_one_or_none()
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
    session.flush()
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
