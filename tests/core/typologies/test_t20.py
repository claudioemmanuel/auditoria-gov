"""Tests for T20 Phantom Bidder typology."""
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from openwatch_models.orm import Event, EventParticipant
from openwatch_models.signals import SignalSeverity
from openwatch_typologies.t20_phantom_bidders import T20PhantomBidderTypology


def _now():
    return datetime.now(timezone.utc)


def _licitacao(*, situacao: str = "Homologada", days_ago: int = 10):
    return Event(
        id=uuid.uuid4(),
        type="licitacao",
        occurred_at=_now() - timedelta(days=days_ago),
        source_connector="pncp",
        source_id=f"lic:{uuid.uuid4()}",
        value_brl=50_000.0,
        attrs={"situacao": situacao, "catmat_group": "group_x"},
    )


def _participant(event_id, entity_id, role: str) -> EventParticipant:
    return EventParticipant(
        id=uuid.uuid4(), event_id=event_id, entity_id=entity_id, role=role, attrs={}
    )


class _Scalars:
    def __init__(self, values):
        self._values = values

    def scalars(self):
        return self

    def all(self):
        return self._values


class _FakeSession:
    def __init__(self, responses):
        self._responses = list(responses)

    async def execute(self, _stmt):
        return _Scalars(self._responses.pop(0))


@pytest.mark.asyncio
async def test_t20_zero_too_few_events():
    events = [_licitacao() for _ in range(4)]
    session = _FakeSession([events, []])
    signals = await T20PhantomBidderTypology().run(session)
    assert signals == []


@pytest.mark.asyncio
async def test_t20_zero_bidder_has_a_win():
    winner_id = uuid.uuid4()
    phantom_id = uuid.uuid4()
    events = [_licitacao(days_ago=i * 10) for i in range(5)]
    participants = []
    for e in events:
        participants.append(_participant(e.id, winner_id, "winner"))
        participants.append(_participant(e.id, phantom_id, "bidder"))
    # Give phantom a win on first event
    participants.append(_participant(events[0].id, phantom_id, "winner"))
    session = _FakeSession([events, participants])
    signals = await T20PhantomBidderTypology().run(session)
    phantom_signals = [s for s in signals if s.factors.get("phantom_entity_id") == str(phantom_id)]
    assert phantom_signals == []


@pytest.mark.asyncio
async def test_t20_zero_low_dominant_win_rate():
    phantom_id = uuid.uuid4()
    winner_a = uuid.uuid4()
    winner_b = uuid.uuid4()
    events = [_licitacao(days_ago=i * 10) for i in range(10)]
    participants = []
    for i, e in enumerate(events):
        participants.append(_participant(e.id, phantom_id, "bidder"))
        participants.append(_participant(e.id, winner_a if i % 2 == 0 else winner_b, "winner"))
    session = _FakeSession([events, participants])
    signals = await T20PhantomBidderTypology().run(session)
    phantom_signals = [s for s in signals if s.factors.get("phantom_entity_id") == str(phantom_id)]
    assert phantom_signals == []


@pytest.mark.asyncio
async def test_t20_positive_medium_severity():
    phantom_id = uuid.uuid4()
    winner_id = uuid.uuid4()
    events = [_licitacao(days_ago=i * 10) for i in range(7)]
    participants = []
    for e in events:
        participants.append(_participant(e.id, phantom_id, "bidder"))
        participants.append(_participant(e.id, winner_id, "winner"))
    session = _FakeSession([events, participants])
    signals = await T20PhantomBidderTypology().run(session)
    phantom_signals = [s for s in signals if s.factors.get("phantom_entity_id") == str(phantom_id)]
    assert len(phantom_signals) == 1
    sig = phantom_signals[0]
    assert sig.severity == SignalSeverity.MEDIUM
    assert sig.factors["participation_count"] == 7
    assert sig.factors["win_rate"] == 0.0
    assert sig.factors["dominant_partner_win_rate"] == pytest.approx(1.0)


@pytest.mark.asyncio
async def test_t20_positive_high_severity():
    phantom_id = uuid.uuid4()
    winner_id = uuid.uuid4()
    events = [_licitacao(days_ago=i * 5) for i in range(12)]
    participants = []
    for e in events:
        participants.append(_participant(e.id, phantom_id, "bidder"))
        participants.append(_participant(e.id, winner_id, "winner"))
    session = _FakeSession([events, participants])
    signals = await T20PhantomBidderTypology().run(session)
    phantom_signals = [s for s in signals if s.factors.get("phantom_entity_id") == str(phantom_id)]
    assert len(phantom_signals) == 1
    assert phantom_signals[0].severity == SignalSeverity.HIGH


@pytest.mark.asyncio
async def test_t20_boundary_exactly_at_threshold():
    phantom_id = uuid.uuid4()
    winner_a = uuid.uuid4()
    winner_b = uuid.uuid4()
    # 5 events: winner_a wins 3 (60%), winner_b wins 2
    events = [_licitacao(days_ago=i * 10) for i in range(5)]
    participants = []
    for i, e in enumerate(events):
        participants.append(_participant(e.id, phantom_id, "bidder"))
        participants.append(_participant(e.id, winner_a if i < 3 else winner_b, "winner"))
    session = _FakeSession([events, participants])
    signals = await T20PhantomBidderTypology().run(session)
    phantom_signals = [s for s in signals if s.factors.get("phantom_entity_id") == str(phantom_id)]
    assert len(phantom_signals) == 1
    assert phantom_signals[0].factors["dominant_partner_win_rate"] == pytest.approx(0.6)


@pytest.mark.asyncio
async def test_t20_zero_void_events_filtered():
    phantom_id = uuid.uuid4()
    winner_id = uuid.uuid4()
    valid_events = [_licitacao(days_ago=i * 10) for i in range(4)]
    void_events = [_licitacao(situacao="cancelada", days_ago=i * 10 + 5) for i in range(3)]
    all_events = valid_events + void_events
    participants = []
    for e in all_events:
        participants.append(_participant(e.id, phantom_id, "bidder"))
        participants.append(_participant(e.id, winner_id, "winner"))
    session = _FakeSession([all_events, participants])
    signals = await T20PhantomBidderTypology().run(session)
    phantom_signals = [s for s in signals if s.factors.get("phantom_entity_id") == str(phantom_id)]
    assert phantom_signals == []
