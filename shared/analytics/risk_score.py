"""Composite risk scoring for entities.

Aggregates all risk signals for an entity, weighted by:
- Severity (critical > high > medium > low)
- Confidence (0-1)
- Recency (newer signals weighted higher)

Produces a normalized 0-100 risk score.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.orm import Entity, RiskSignal


# Severity weights
_SEVERITY_WEIGHTS = {
    "critical": 4.0,
    "high": 3.0,
    "medium": 2.0,
    "low": 1.0,
}

# Recency decay: signals lose weight over time
_RECENCY_HALF_LIFE_DAYS = 180  # 6 months


def _recency_weight(signal_date: datetime | None) -> float:
    """Compute recency weight with exponential decay."""
    if signal_date is None:
        return 0.5  # Default weight for undated signals

    now = datetime.now(timezone.utc)
    if signal_date.tzinfo is None:
        signal_date = signal_date.replace(tzinfo=timezone.utc)

    age_days = max(0, (now - signal_date).days)
    import math
    return math.exp(-0.693 * age_days / _RECENCY_HALF_LIFE_DAYS)


def compute_risk_score_from_signals(signals: list[dict]) -> float:
    """Compute a 0-100 risk score from a list of signal dicts.

    Each signal dict should have: severity, confidence, created_at (optional).
    """
    if not signals:
        return 0.0

    total_weighted = 0.0
    max_possible = 0.0

    for s in signals:
        severity = s.get("severity", "low")
        confidence = s.get("confidence", 0.5)
        created_at = s.get("created_at")

        sev_weight = _SEVERITY_WEIGHTS.get(severity, 1.0)
        recency = _recency_weight(created_at)

        weighted = sev_weight * confidence * recency
        total_weighted += weighted
        max_possible += _SEVERITY_WEIGHTS["critical"] * 1.0 * 1.0

    if max_possible <= 0:
        return 0.0

    # Normalize to 0-100 with diminishing returns
    raw_score = total_weighted / max(1.0, len(signals) * 0.5)  # Adjusted normalization
    import math
    normalized = 100 * (1 - math.exp(-raw_score / 2))

    return round(min(100.0, max(0.0, normalized)), 2)


async def compute_entity_risk_score(
    entity_id: uuid.UUID,
    session: AsyncSession,
) -> float:
    """Compute and store risk score for an entity.

    Aggregates all signals referencing this entity,
    weights by severity + confidence + recency,
    normalizes to 0-100 scale.
    """
    # Get all signals mentioning this entity
    stmt = select(RiskSignal).order_by(RiskSignal.created_at.desc()).limit(100)
    result = await session.execute(stmt)
    all_signals = result.scalars().all()

    entity_id_str = str(entity_id)
    entity_signals = [
        {
            "severity": s.severity,
            "confidence": s.confidence,
            "created_at": s.created_at,
        }
        for s in all_signals
        if entity_id_str in [str(eid) for eid in s.entity_ids]
    ]

    score = compute_risk_score_from_signals(entity_signals)

    # Update entity attrs with risk score
    entity_stmt = select(Entity).where(Entity.id == entity_id)
    entity_result = await session.execute(entity_stmt)
    entity = entity_result.scalar_one_or_none()

    if entity is not None:
        entity.attrs = {**entity.attrs, "risk_score": score}
        await session.flush()

    return score
