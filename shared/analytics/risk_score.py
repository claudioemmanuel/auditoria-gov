"""Composite risk scoring for entities.

Aggregates all risk signals for an entity, weighted by:
- Severity (critical > high > medium > low)
- Confidence (0-1)
- Recency (newer signals weighted higher)
- Typology weight (some typologies carry more legal gravity)

Produces a normalized 0-100 risk score.
"""

import math
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.orm import Entity, EventParticipant, GraphEdge, GraphNode, RiskSignal
from shared.repo.queries import resolve_entity_ids_with_clusters


# Severity weights
_SEVERITY_WEIGHTS = {
    "critical": 4.0,
    "high": 3.0,
    "medium": 2.0,
    "low": 1.0,
}

# Recency decay: signals lose weight over time
_RECENCY_HALF_LIFE_DAYS = 180  # 6 months

# Typology weights — reflect relative legal gravity of each typology
TYPOLOGY_WEIGHTS: dict[str, float] = {
    "T07": 0.90,
    "T13": 0.85,
    "T11": 0.80,
    "T14": 0.80,
    "T17": 0.80,
    "T12": 0.75,
    "T08": 0.75,
    "T15": 0.70,
    "T03": 0.70,
    "T06": 0.65,
    "T09": 0.65,
    "T18": 0.65,
    "T05": 0.60,
    "T04": 0.60,
    "T10": 0.55,
    "T02": 0.60,
    "T01": 0.50,
}
_DEFAULT_TYPOLOGY_WEIGHT = 0.50


def _recency_weight(signal_date: datetime | None) -> float:
    """Compute recency weight with exponential decay."""
    if signal_date is None:
        return 0.5  # Default weight for undated signals

    now = datetime.now(timezone.utc)
    if signal_date.tzinfo is None:
        signal_date = signal_date.replace(tzinfo=timezone.utc)

    age_days = max(0, (now - signal_date).days)
    return math.exp(-0.693 * age_days / _RECENCY_HALF_LIFE_DAYS)


def compute_risk_score_from_signals(signals: list[dict]) -> float:
    """Compute a 0-100 risk score from a list of signal dicts.

    Each signal dict should have: severity, confidence, created_at (optional),
    typology_code (optional).

    typology_code is used to look up a typology-specific weight from
    TYPOLOGY_WEIGHTS; missing or unknown codes fall back to the default weight.
    """
    if not signals:
        return 0.0

    total_weighted = 0.0

    for s in signals:
        severity = s.get("severity", "low")
        confidence = s.get("confidence", 0.5)
        created_at = s.get("created_at")
        typology_code = s.get("typology_code")

        sev_weight = _SEVERITY_WEIGHTS.get(severity, 1.0)
        recency = _recency_weight(created_at)
        typology_weight = TYPOLOGY_WEIGHTS.get(typology_code or "", _DEFAULT_TYPOLOGY_WEIGHT)

        weighted = sev_weight * confidence * recency * typology_weight
        total_weighted += weighted

    # Normalize to 0-100 with diminishing returns
    raw_score = total_weighted / max(1.0, len(signals) * 0.5)  # Adjusted normalization
    normalized = 100 * (1 - math.exp(-raw_score / 2))

    return round(min(100.0, max(0.0, normalized)), 2)


async def compute_entity_risk_score(
    entity_id: uuid.UUID,
    session: AsyncSession,
) -> float:
    """Compute and store risk score for an entity.

    Aggregates all signals referencing this entity,
    weights by severity + confidence + recency + typology,
    adds network degree factor and sanction factor,
    normalizes to 0-100 scale.
    """
    # Get all signals mentioning this entity (including cluster siblings)
    resolved_ids = await resolve_entity_ids_with_clusters(session, [entity_id])
    stmt = select(RiskSignal).order_by(RiskSignal.created_at.desc()).limit(100)
    result = await session.execute(stmt)
    all_signals = result.scalars().all()

    entity_signals = [
        {
            "severity": s.severity,
            "confidence": s.confidence,
            "created_at": s.created_at,
            "typology_code": s.typology.code if s.typology is not None else None,
        }
        for s in all_signals
        if resolved_ids.intersection(
            uuid.UUID(str(eid)) for eid in (s.entity_ids or [])
        )
    ]

    signal_score_raw = compute_risk_score_from_signals(entity_signals)

    # Network degree factor: count GraphEdges touching this entity's GraphNode
    node_subq = (
        select(GraphNode.id)
        .where(GraphNode.entity_id == entity_id)
        .scalar_subquery()
    )
    degree_stmt = select(func.count()).select_from(GraphEdge).where(
        or_(
            GraphEdge.from_node_id == node_subq,
            GraphEdge.to_node_id == node_subq,
        )
    )
    degree_result = await session.execute(degree_stmt)
    degree: int = degree_result.scalar_one() or 0
    network_factor = min(1.0, degree * 0.05)

    # Sanction factor: check if entity has any sancao event via EventParticipant
    from shared.models.orm import Event  # local import to avoid circular at module level

    sanction_stmt = (
        select(func.count())
        .select_from(EventParticipant)
        .join(Event, Event.id == EventParticipant.event_id)
        .where(
            EventParticipant.entity_id == entity_id,
            Event.type == "sancao",
        )
    )
    sanction_result = await session.execute(sanction_stmt)
    sanction_count: int = sanction_result.scalar_one() or 0
    sanction_factor = 1.5 if sanction_count > 0 else 0.0

    # Combine signal score with network and sanction factors
    # signal_score_raw is already 0-100; convert back to raw additive scale
    raw = signal_score_raw + network_factor + sanction_factor
    normalized = 100 * (1 - math.exp(-raw / 2))
    score = round(min(100.0, max(0.0, normalized)), 2)

    # Update entity attrs with risk score
    entity_stmt = select(Entity).where(Entity.id == entity_id)
    entity_result = await session.execute(entity_stmt)
    entity = entity_result.scalar_one_or_none()

    if entity is not None:
        entity.attrs = {**entity.attrs, "risk_score": score}
        await session.flush()

    return score
