"""Tests for T26 — State Audit Court Penalty x Active Contract Mismatch."""
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from shared.models.signals import SignalSeverity
from shared.typologies.t26_state_penalty_mismatch import T26StatePenaltyMismatchTypology


# ── Fake ORM session infrastructure ──────────────────────────────────────────


class _Scalars:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


class _FakeSession:
    def __init__(self, responses):
        self._q = list(responses)

    async def execute(self, *_, **__):
        return _Scalars(self._q.pop(0))


# ── Fake ORM object factories ────────────────────────────────────────────────


def _now():
    return datetime.now(timezone.utc)


def _penalty_event(
    *,
    entity_id,
    start_days_ago=365,
    end_days_from_now=365,
    indefinite=False,
    penalty_type="multa",
):
    eid = uuid.uuid4()
    start = _now() - timedelta(days=start_days_ago)
    end = None if indefinite else (_now() + timedelta(days=end_days_from_now))
    event = SimpleNamespace(
        id=eid,
        type="penalidade_tce_rj",
        attrs={
            "penalty_start": start.isoformat(),
            "penalty_end": end.isoformat() if end else None,
            "penalty_type": penalty_type,
        },
        occurred_at=start,
        description="Penalidade TCE-RJ",
        value_brl=None,
    )
    participant = SimpleNamespace(
        id=uuid.uuid4(),
        event_id=eid,
        entity_id=entity_id,
        role="penalizado",
    )
    return event, participant


def _contract_event(
    *,
    entity_id,
    start_days_ago=30,
    end_days_from_now=335,
    value_brl=200_000.0,
):
    eid = uuid.uuid4()
    start = _now() - timedelta(days=start_days_ago)
    end = _now() + timedelta(days=end_days_from_now)
    event = SimpleNamespace(
        id=eid,
        type="contrato",
        attrs={
            "contract_start": start.isoformat(),
            "contract_end": end.isoformat(),
        },
        occurred_at=start,
        value_brl=value_brl,
    )
    participant = SimpleNamespace(
        id=uuid.uuid4(),
        event_id=eid,
        entity_id=entity_id,
        role="supplier",
    )
    return event, participant


# ── Zero-result cases ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_zero_no_penalties():
    """No penalidade_tce_rj events → early exit."""
    session = _FakeSession([[]])
    signals = await T26StatePenaltyMismatchTypology().run(session)
    assert signals == []


@pytest.mark.asyncio
async def test_zero_no_contracts():
    """Penalties exist but no contracts → no signals."""
    entity_id = uuid.uuid4()
    p, pp = _penalty_event(entity_id=entity_id)
    session = _FakeSession([[p], [pp], []])
    signals = await T26StatePenaltyMismatchTypology().run(session)
    assert signals == []


@pytest.mark.asyncio
async def test_zero_no_matching_entity():
    """Penalties and contracts exist for different entities → no signals."""
    penalty_entity = uuid.uuid4()
    contract_entity = uuid.uuid4()
    p, pp = _penalty_event(entity_id=penalty_entity)
    c, cp = _contract_event(entity_id=contract_entity)
    session = _FakeSession([[p], [pp], [c], [cp]])
    signals = await T26StatePenaltyMismatchTypology().run(session)
    assert signals == []


# ── Positive cases ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_critical_active_penalty_active_contract():
    """Active penalty + active contract → CRITICAL signal."""
    entity_id = uuid.uuid4()
    p, pp = _penalty_event(entity_id=entity_id, start_days_ago=180, end_days_from_now=180)
    c, cp = _contract_event(entity_id=entity_id, start_days_ago=30)
    session = _FakeSession([[p], [pp], [c], [cp]])

    signals = await T26StatePenaltyMismatchTypology().run(session)

    assert len(signals) == 1
    sig = signals[0]
    assert sig.severity == SignalSeverity.CRITICAL
    assert sig.typology_code == "T26"
    assert sig.factors["penalty_active_now"] is True
    assert sig.confidence == 0.95


@pytest.mark.asyncio
async def test_high_expired_penalty_active_contract():
    """Penalty expired recently + active contract → HIGH signal."""
    entity_id = uuid.uuid4()
    # Penalty ended 60 days ago (expired but overlap still occurs)
    p, pp = _penalty_event(entity_id=entity_id, start_days_ago=400, end_days_from_now=-60)
    c, cp = _contract_event(entity_id=entity_id, start_days_ago=500, end_days_from_now=200)
    session = _FakeSession([[p], [pp], [c], [cp]])

    signals = await T26StatePenaltyMismatchTypology().run(session)

    assert len(signals) == 1
    sig = signals[0]
    assert sig.severity == SignalSeverity.HIGH
    assert sig.factors["penalty_active_now"] is False
    assert sig.confidence == 0.85


@pytest.mark.asyncio
async def test_indefinite_penalty():
    """Penalty with no end date (ongoing) + active contract → CRITICAL."""
    entity_id = uuid.uuid4()
    p, pp = _penalty_event(entity_id=entity_id, start_days_ago=180, indefinite=True)
    c, cp = _contract_event(entity_id=entity_id, start_days_ago=30)
    session = _FakeSession([[p], [pp], [c], [cp]])

    signals = await T26StatePenaltyMismatchTypology().run(session)

    assert len(signals) == 1
    assert signals[0].severity == SignalSeverity.CRITICAL


# ── Metadata ─────────────────────────────────────────────────────────────────


def test_t26_metadata():
    t = T26StatePenaltyMismatchTypology()
    assert t.id == "T26"
    assert "TCE" in t.name or "Penalidade" in t.name
    assert "penalidade_tce_rj" in t.required_domains
    assert "contrato" in t.required_domains
    assert "fraude_licitatoria" in t.corruption_types
    assert t.evidence_level == "direct"
