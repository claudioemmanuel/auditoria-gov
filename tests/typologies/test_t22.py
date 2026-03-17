"""Tests for T22 Political Favoritism typology."""
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from shared.models.orm import Event, EventParticipant
from shared.models.signals import SignalSeverity
from shared.typologies.t22_political_favoritism import T22PoliticalFavoritismTypology


def _now():
    return datetime.now(timezone.utc)


def _donation_event(*, days_ago: int, company_id: uuid.UUID, value: float = 10_000.0):
    e = Event(
        id=uuid.uuid4(), type="doacao_eleitoral",
        occurred_at=_now() - timedelta(days=days_ago),
        source_connector="tse", source_id=f"don:{uuid.uuid4()}",
        value_brl=value, attrs={},
    )
    p = EventParticipant(id=uuid.uuid4(), event_id=e.id, entity_id=company_id, role="donor", attrs={})
    return e, p


def _contract_event(*, days_ago: int, company_id: uuid.UUID, value: float = 500_000.0):
    e = Event(
        id=uuid.uuid4(), type="contrato",
        occurred_at=_now() - timedelta(days=days_ago),
        source_connector="pncp", source_id=f"con:{uuid.uuid4()}",
        value_brl=value, attrs={},
    )
    p = EventParticipant(id=uuid.uuid4(), event_id=e.id, entity_id=company_id, role="supplier", attrs={})
    return e, p


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
async def test_t22_zero_no_donations():
    session = _FakeSession([[]])
    signals = await T22PoliticalFavoritismTypology().run(session)
    assert signals == []


@pytest.mark.asyncio
async def test_t22_zero_delta_too_large():
    company_id = uuid.uuid4()
    don, dp = _donation_event(days_ago=800, company_id=company_id)
    con, cp = _contract_event(days_ago=10, company_id=company_id)
    session = _FakeSession([[don], [con], [dp], [cp]])
    signals = await T22PoliticalFavoritismTypology().run(session)
    assert signals == []


@pytest.mark.asyncio
async def test_t22_zero_only_one_pair():
    company_id = uuid.uuid4()
    don, dp = _donation_event(days_ago=400, company_id=company_id)
    con, cp = _contract_event(days_ago=100, company_id=company_id)
    session = _FakeSession([[don], [con], [dp], [cp]])
    signals = await T22PoliticalFavoritismTypology().run(session)
    assert signals == []


@pytest.mark.asyncio
async def test_t22_positive_high_severity():
    company_id = uuid.uuid4()
    don1, dp1 = _donation_event(days_ago=300, company_id=company_id, value=5_000.0)
    don2, dp2 = _donation_event(days_ago=310, company_id=company_id, value=8_000.0)
    con1, cp1 = _contract_event(days_ago=50, company_id=company_id, value=200_000.0)
    con2, cp2 = _contract_event(days_ago=60, company_id=company_id, value=300_000.0)
    session = _FakeSession([[don1, don2], [con1, con2], [dp1, dp2], [cp1, cp2]])
    signals = await T22PoliticalFavoritismTypology().run(session)
    assert len(signals) == 1
    sig = signals[0]
    assert sig.severity == SignalSeverity.HIGH
    assert sig.factors["company_entity_id"] == str(company_id)
    assert sig.factors["n_donation_contract_pairs"] >= 2
    assert sig.factors["avg_delta_months"] <= 12.0


@pytest.mark.asyncio
async def test_t22_positive_medium_severity():
    company_id = uuid.uuid4()
    don1, dp1 = _donation_event(days_ago=600, company_id=company_id)
    don2, dp2 = _donation_event(days_ago=610, company_id=company_id)
    con1, cp1 = _contract_event(days_ago=50, company_id=company_id)
    con2, cp2 = _contract_event(days_ago=60, company_id=company_id)
    session = _FakeSession([[don1, don2], [con1, con2], [dp1, dp2], [cp1, cp2]])
    signals = await T22PoliticalFavoritismTypology().run(session)
    assert len(signals) == 1
    sig = signals[0]
    assert sig.severity == SignalSeverity.MEDIUM
    assert 12.0 < sig.factors["avg_delta_months"] <= 24.0


@pytest.mark.asyncio
async def test_t22_boundary_exactly_730_days():
    company_id = uuid.uuid4()
    # Use a fixed reference time so delta is deterministic (730 days exactly)
    ref = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    don1, dp1 = _donation_event(days_ago=1, company_id=company_id)
    don2, dp2 = _donation_event(days_ago=1, company_id=company_id)
    con1, cp1 = _contract_event(days_ago=1, company_id=company_id)
    con2, cp2 = _contract_event(days_ago=1, company_id=company_id)
    # Set occurred_at directly for precise control
    don1.occurred_at = ref
    don2.occurred_at = ref - timedelta(days=5)
    con1.occurred_at = ref + timedelta(days=730)   # exactly 730 days after donation → boundary
    con2.occurred_at = ref + timedelta(days=725)
    session = _FakeSession([[don1, don2], [con1, con2], [dp1, dp2], [cp1, cp2]])
    signals = await T22PoliticalFavoritismTypology().run(session)
    assert len(signals) == 1


@pytest.mark.asyncio
async def test_t22_zero_contract_before_donation():
    company_id = uuid.uuid4()
    # Contracts 400 days ago, donations 100 days ago → delta negative → no pairs
    don1, dp1 = _donation_event(days_ago=100, company_id=company_id)
    don2, dp2 = _donation_event(days_ago=110, company_id=company_id)
    con1, cp1 = _contract_event(days_ago=400, company_id=company_id)
    con2, cp2 = _contract_event(days_ago=410, company_id=company_id)
    session = _FakeSession([[don1, don2], [con1, con2], [dp1, dp2], [cp1, cp2]])
    signals = await T22PoliticalFavoritismTypology().run(session)
    assert signals == []
