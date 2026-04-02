"""Tests for T21 Collusive Cluster typology."""
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from openwatch_models.orm import Event, EventParticipant
from openwatch_models.signals import SignalSeverity
from openwatch_typologies.t21_collusive_cluster import T21CollusiveClusterTypology, _is_uuid


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now():
    return datetime.now(timezone.utc)


def _licitacao(*, situacao: str = "Homologada", catmat: str = "catmat_A", value: float = 50_000.0):
    return Event(
        id=uuid.uuid4(),
        type="licitacao",
        occurred_at=_now() - timedelta(days=30),
        source_connector="pncp",
        source_id=f"lic:{uuid.uuid4()}",
        value_brl=value,
        attrs={"situacao": situacao, "catmat_group": catmat},
    )


def _participant(event_id: uuid.UUID, entity_id: uuid.UUID, role: str) -> EventParticipant:
    return EventParticipant(
        id=uuid.uuid4(),
        event_id=event_id,
        entity_id=entity_id,
        role=role,
        attrs={},
    )


class _ScalarResult:
    def __init__(self, values):
        self._values = values

    def scalars(self):
        return self

    def all(self):
        return self._values


class _FakeAsyncSession:
    """Fake async session that pops responses in order."""

    def __init__(self, responses):
        self._responses = list(responses)

    async def execute(self, _stmt):
        if not self._responses:
            raise AssertionError("No fake response available for execute()")
        return _ScalarResult(self._responses.pop(0))


# ---------------------------------------------------------------------------
# Test: Zero-result — win rate below threshold
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_t21_no_signal_low_win_rate():
    """Community with intra_cluster_win_rate < 0.80 → no signal.

    Use 10 events. Three cluster members (A/B/C) bid together on all 10.
    Five independent outsiders each bid on only 1 event (so they never
    co-bid with each other ≥ 2 times → they don't form graph edges and stay
    outside the detected community). Each outsider wins their single event.
    Cluster wins only 2 events → rate = 2 / 7 ≈ 0.29 < 0.80.
    """
    company_a = uuid.uuid4()
    company_b = uuid.uuid4()
    company_c = uuid.uuid4()
    # 5 independent outsiders — each only bids once so no co-bid edges
    outsiders = [uuid.uuid4() for _ in range(5)]

    events = [_licitacao() for _ in range(10)]
    participants = []

    for i, e in enumerate(events):
        # Cluster members bid all events (form strong community)
        for comp in (company_a, company_b, company_c):
            participants.append(_participant(e.id, comp, "bidder"))
        # First 5 events: one unique outsider bids and wins → cluster can't win these
        if i < 5:
            outsider = outsiders[i]
            participants.append(_participant(e.id, outsider, "bidder"))
            participants.append(_participant(e.id, outsider, "winner"))
        elif i < 7:
            # Events 5 and 6: cluster member wins → cluster wins = 2
            participants.append(_participant(e.id, company_a, "winner"))
        # Events 7-9: no winner recorded

    # total_wins = 5 (outsider) + 2 (cluster) = 7
    # cluster wins = 2 → rate = 2/7 ≈ 0.29 < 0.80

    session = _FakeAsyncSession([events, participants, []])
    signals = await T21CollusiveClusterTypology().run(session)
    assert signals == []


# ---------------------------------------------------------------------------
# Test: Zero-result — fewer than 5 procurements in community scope
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_t21_no_signal_too_few_procurements():
    """Community with win rate >= 0.80 but only 4 procurements → no signal."""
    company_a = uuid.uuid4()
    company_b = uuid.uuid4()
    company_c = uuid.uuid4()

    events = [_licitacao() for _ in range(4)]
    participants = []

    for e in events:
        for comp in (company_a, company_b, company_c):
            participants.append(_participant(e.id, comp, "bidder"))
        participants.append(_participant(e.id, company_a, "winner"))

    session = _FakeAsyncSession([events, participants, []])
    signals = await T21CollusiveClusterTypology().run(session)
    assert signals == []


# ---------------------------------------------------------------------------
# Test: Positive — 3+ companies, win_rate >= 0.80, >= 5 procurements
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_t21_positive_high_severity():
    """3 companies with win_rate = 1.0 across 5 procurements → HIGH signal."""
    company_a = uuid.uuid4()
    company_b = uuid.uuid4()
    company_c = uuid.uuid4()

    events = [_licitacao() for _ in range(5)]
    participants = []

    for e in events:
        for comp in (company_a, company_b, company_c):
            participants.append(_participant(e.id, comp, "bidder"))
        # Community wins every event → win rate = 5/5 = 1.0
        participants.append(_participant(e.id, company_a, "winner"))

    session = _FakeAsyncSession([events, participants, []])
    signals = await T21CollusiveClusterTypology().run(session)

    assert len(signals) == 1
    sig = signals[0]
    assert sig.typology_code == "T21"
    assert sig.severity == SignalSeverity.HIGH  # cluster_size=3, need >=5 for CRITICAL
    assert sig.factors["intra_cluster_win_rate"] == 1.0
    assert sig.factors["n_procurements"] == 5
    assert sig.factors["cluster_size"] == 3


# ---------------------------------------------------------------------------
# Test: CRITICAL — cluster_size >= 5 AND win_rate >= 0.90
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_t21_critical_large_cluster():
    """5 companies with win_rate >= 0.90 across 10 procurements → CRITICAL signal."""
    companies = [uuid.uuid4() for _ in range(5)]

    events = [_licitacao() for _ in range(10)]
    participants = []

    for i, e in enumerate(events):
        for comp in companies:
            participants.append(_participant(e.id, comp, "bidder"))
        # 9 out of 10 won by cluster → win_rate = 0.90
        if i < 9:
            participants.append(_participant(e.id, companies[0], "winner"))

    session = _FakeAsyncSession([events, participants, []])
    signals = await T21CollusiveClusterTypology().run(session)

    assert len(signals) == 1
    sig = signals[0]
    assert sig.severity == SignalSeverity.CRITICAL
    assert sig.factors["cluster_size"] == 5
    assert sig.factors["intra_cluster_win_rate"] >= 0.90


# ---------------------------------------------------------------------------
# Test: Boundary — exactly at threshold (80% win rate, 5 procurements)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_t21_boundary_exact_threshold():
    """Exactly 80% win rate with 5 procurements → signal fires (boundary)."""
    company_a = uuid.uuid4()
    company_b = uuid.uuid4()
    company_c = uuid.uuid4()
    outsider = uuid.uuid4()

    events = [_licitacao() for _ in range(5)]
    participants = []

    for i, e in enumerate(events):
        for comp in (company_a, company_b, company_c):
            participants.append(_participant(e.id, comp, "bidder"))
        # 4 wins by cluster, 1 by outsider → 4/5 = 0.80
        if i < 4:
            participants.append(_participant(e.id, company_a, "winner"))
        else:
            participants.append(_participant(e.id, outsider, "winner"))

    session = _FakeAsyncSession([events, participants, []])
    signals = await T21CollusiveClusterTypology().run(session)

    assert len(signals) == 1
    assert signals[0].factors["intra_cluster_win_rate"] == pytest.approx(0.80, abs=1e-4)


# ---------------------------------------------------------------------------
# Test: Zero-result — fewer than 3 events total
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_t21_no_signal_too_few_events():
    """Less than 3 licitacao events → early return []."""
    events = [_licitacao(), _licitacao()]
    session = _FakeAsyncSession([events])
    signals = await T21CollusiveClusterTypology().run(session)
    assert signals == []


# ---------------------------------------------------------------------------
# Test: Zero-result — all events are void
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_t21_no_signal_all_void():
    """All licitacao events with situacao=Cancelada → no signal (void filtered)."""
    events = [_licitacao(situacao="Cancelada") for _ in range(5)]
    participants = []

    company_a = uuid.uuid4()
    company_b = uuid.uuid4()
    company_c = uuid.uuid4()

    for e in events:
        for comp in (company_a, company_b, company_c):
            participants.append(_participant(e.id, comp, "bidder"))
        participants.append(_participant(e.id, company_a, "winner"))

    session = _FakeAsyncSession([events, participants])
    signals = await T21CollusiveClusterTypology().run(session)
    assert signals == []


# ---------------------------------------------------------------------------
# Test: T07 dedup — community is subset of T07 signal entity_ids → skipped
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_t21_deduplication_vs_t07():
    """Community is a subset of an existing T07 signal → signal skipped."""
    company_a = uuid.uuid4()
    company_b = uuid.uuid4()
    company_c = uuid.uuid4()

    events = [_licitacao() for _ in range(5)]
    participants = []

    for e in events:
        for comp in (company_a, company_b, company_c):
            participants.append(_participant(e.id, comp, "bidder"))
        participants.append(_participant(e.id, company_a, "winner"))

    # Create a fake T07 RiskSignal whose entity_ids include all community members
    fake_t07_signal = MagicMock()
    fake_t07_signal.entity_ids = [company_a, company_b, company_c, uuid.uuid4()]

    session = _FakeAsyncSession([events, participants, [fake_t07_signal]])
    signals = await T21CollusiveClusterTypology().run(session)
    assert signals == []


# ---------------------------------------------------------------------------
# Test: networkx ImportError fallback path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_t21_networkx_import_error_fallback(monkeypatch):
    """When networkx is unavailable, fallback connected-components logic fires."""
    import builtins
    real_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == "networkx":
            raise ImportError("networkx not available")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mock_import)

    company_a = uuid.uuid4()
    company_b = uuid.uuid4()
    company_c = uuid.uuid4()

    events = [_licitacao() for _ in range(5)]
    participants = []

    for e in events:
        for comp in (company_a, company_b, company_c):
            participants.append(_participant(e.id, comp, "bidder"))
        participants.append(_participant(e.id, company_a, "winner"))

    session = _FakeAsyncSession([events, participants, []])
    signals = await T21CollusiveClusterTypology().run(session)

    # Fallback should still detect the cluster
    assert len(signals) == 1


# ---------------------------------------------------------------------------
# Test: _is_uuid helper
# ---------------------------------------------------------------------------


def test_is_uuid_valid():
    assert _is_uuid(str(uuid.uuid4())) is True


def test_is_uuid_invalid():
    assert _is_uuid("not-a-uuid") is False
