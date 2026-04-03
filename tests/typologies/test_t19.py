"""Tests for T19 Bid Rotation typology."""
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from shared.models.orm import Event, EventParticipant
from shared.models.signals import SignalSeverity
from shared.typologies.t19_bid_rotation import T19BidRotationTypology


class _ScalarResult:
    def __init__(self, values):
        self._values = values

    def scalars(self):
        return self

    def all(self):
        return self._values


class _FakeAsyncSession:
    def __init__(self, responses):
        self._responses = list(responses)

    async def execute(self, _stmt):
        if not self._responses:
            raise AssertionError("No fake response available for execute()")
        return _ScalarResult(self._responses.pop(0))


def _now():
    return datetime.now(timezone.utc)


def _licitacao(*, situacao: str = "Homologada", catmat_group: str = "group_x", days_ago: int = 5):
    return Event(
        id=uuid.uuid4(),
        type="licitacao",
        occurred_at=_now() - timedelta(days=days_ago),
        source_connector="pncp",
        source_id=f"lic:{uuid.uuid4()}",
        value_brl=50_000.0,
        attrs={"situacao": situacao, "catmat_group": catmat_group},
    )


def _winner(event_id: uuid.UUID, entity_id: uuid.UUID) -> EventParticipant:
    return EventParticipant(
        id=uuid.uuid4(), event_id=event_id, entity_id=entity_id, role="winner", attrs={}
    )


def _buyer(event_id: uuid.UUID, entity_id: uuid.UUID) -> EventParticipant:
    return EventParticipant(
        id=uuid.uuid4(), event_id=event_id, entity_id=entity_id, role="buyer", attrs={}
    )


# ---------------------------------------------------------------------------
# Zero-result tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_t19_zero_result_too_few_events():
    """Fewer than 4 events in total → no signals."""
    buyer_id = uuid.uuid4()
    winner_a = uuid.uuid4()
    winner_b = uuid.uuid4()
    events = [_licitacao(days_ago=10 * i) for i in range(1, 4)]  # 3 events
    participants = []
    for i, e in enumerate(events):
        w = winner_a if i % 2 == 0 else winner_b
        participants.append(_winner(e.id, w))
        participants.append(_buyer(e.id, buyer_id))

    session = _FakeAsyncSession([events, participants])
    signals = await T19BidRotationTypology().run(session)
    assert signals == []


@pytest.mark.asyncio
async def test_t19_zero_result_group_fewer_than_4():
    """4 events total but split across different catmat_groups → no group has >= 4."""
    buyer_id = uuid.uuid4()
    winner_a = uuid.uuid4()
    winner_b = uuid.uuid4()
    # 2 events for group_x, 2 for group_y
    e1 = _licitacao(catmat_group="group_x", days_ago=10)
    e2 = _licitacao(catmat_group="group_x", days_ago=20)
    e3 = _licitacao(catmat_group="group_y", days_ago=30)
    e4 = _licitacao(catmat_group="group_y", days_ago=40)
    events = [e1, e2, e3, e4]
    participants = []
    for i, e in enumerate(events):
        w = winner_a if i % 2 == 0 else winner_b
        participants.append(_winner(e.id, w))
        participants.append(_buyer(e.id, buyer_id))

    session = _FakeAsyncSession([events, participants])
    signals = await T19BidRotationTypology().run(session)
    assert signals == []


@pytest.mark.asyncio
async def test_t19_zero_result_void_events():
    """4 events all void → filtered out → no signals."""
    buyer_id = uuid.uuid4()
    winner_a = uuid.uuid4()
    winner_b = uuid.uuid4()
    events = [_licitacao(situacao=s, days_ago=10 * (i + 1)) for i, s in enumerate(
        ["Deserta", "Fracassada", "Revogada", "Cancelada"]
    )]
    participants = []
    for i, e in enumerate(events):
        w = winner_a if i % 2 == 0 else winner_b
        participants.append(_winner(e.id, w))
        participants.append(_buyer(e.id, buyer_id))

    session = _FakeAsyncSession([events, participants])
    signals = await T19BidRotationTypology().run(session)
    assert signals == []


@pytest.mark.asyncio
async def test_t19_zero_result_catmat_missing():
    """Events with CATMAT_MISSING catmat_group are skipped."""
    from shared.baselines.compute import _CATMAT_MISSING
    missing_catmat = next(iter(_CATMAT_MISSING))

    buyer_id = uuid.uuid4()
    winner_a = uuid.uuid4()
    winner_b = uuid.uuid4()
    events = [_licitacao(catmat_group=missing_catmat, days_ago=10 * (i + 1)) for i in range(6)]
    participants = []
    for i, e in enumerate(events):
        w = winner_a if i % 2 == 0 else winner_b
        participants.append(_winner(e.id, w))
        participants.append(_buyer(e.id, buyer_id))

    session = _FakeAsyncSession([events, participants])
    signals = await T19BidRotationTypology().run(session)
    assert signals == []


@pytest.mark.asyncio
async def test_t19_zero_result_entropy_too_high():
    """All different winners → rotation_entropy > 0.65 → no signal."""
    buyer_id = uuid.uuid4()
    # 4 events, 4 unique winners → entropy = 1.0
    events = [_licitacao(days_ago=10 * (i + 1)) for i in range(4)]
    participants = []
    for e in events:
        participants.append(_winner(e.id, uuid.uuid4()))
        participants.append(_buyer(e.id, buyer_id))

    session = _FakeAsyncSession([events, participants])
    signals = await T19BidRotationTypology().run(session)
    assert signals == []


@pytest.mark.asyncio
async def test_t19_zero_result_entropy_too_low():
    """Same winner every time → rotation_entropy < 0.20 → no signal."""
    buyer_id = uuid.uuid4()
    single_winner = uuid.uuid4()
    events = [_licitacao(days_ago=10 * (i + 1)) for i in range(6)]
    participants = []
    for e in events:
        participants.append(_winner(e.id, single_winner))
        participants.append(_buyer(e.id, buyer_id))

    session = _FakeAsyncSession([events, participants])
    signals = await T19BidRotationTypology().run(session)
    assert signals == []


@pytest.mark.asyncio
async def test_t19_zero_result_low_alternation_rate():
    """Entropy in range but alternation_rate < 0.5 → no signal.

    Pattern: A A A B (alternation only at last pair → rate = 1/3 ≈ 0.33).
    """
    buyer_id = uuid.uuid4()
    winner_a = uuid.uuid4()
    winner_b = uuid.uuid4()
    # 4 events; winner sequence: A, A, A, B
    events = [_licitacao(days_ago=40 - i * 10) for i in range(4)]
    events.sort(key=lambda e: e.occurred_at)
    participants = []
    for i, e in enumerate(events):
        w = winner_b if i == 3 else winner_a
        participants.append(_winner(e.id, w))
        participants.append(_buyer(e.id, buyer_id))

    session = _FakeAsyncSession([events, participants])
    signals = await T19BidRotationTypology().run(session)
    assert signals == []


# ---------------------------------------------------------------------------
# Positive tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_t19_high_signal_basic_rotation():
    """6 events with 2 winners alternating perfectly → HIGH signal.

    Sequence A B A B A B: entropy=2/6≈0.33, alternation_rate=1.0.
    """
    buyer_id = uuid.uuid4()
    winner_a = uuid.uuid4()
    winner_b = uuid.uuid4()
    events = [_licitacao(days_ago=60 - i * 10) for i in range(6)]
    events.sort(key=lambda e: e.occurred_at)
    participants = []
    for i, e in enumerate(events):
        w = winner_a if i % 2 == 0 else winner_b
        participants.append(_winner(e.id, w))
        participants.append(_buyer(e.id, buyer_id))

    session = _FakeAsyncSession([events, participants])
    signals = await T19BidRotationTypology().run(session)

    assert len(signals) == 1
    s = signals[0]
    assert s.severity == SignalSeverity.CRITICAL  # alternation>=0.7 and n_procs>=6
    assert s.typology_code == "T19"
    assert s.factors["n_procurements"] == 6
    assert s.factors["n_unique_winners"] == 2
    assert 0.20 <= s.factors["rotation_entropy"] <= 0.65
    assert s.factors["rotation_alternation_rate"] >= 0.7


@pytest.mark.asyncio
async def test_t19_high_signal_3_winner_rotation():
    """6 events with 3 winners in sequence → HIGH or CRITICAL signal.

    Sequence A B C A B C: entropy=3/6=0.5, alternation_rate=1.0.
    """
    buyer_id = uuid.uuid4()
    winner_a = uuid.uuid4()
    winner_b = uuid.uuid4()
    winner_c = uuid.uuid4()
    winners_cycle = [winner_a, winner_b, winner_c, winner_a, winner_b, winner_c]
    events = [_licitacao(days_ago=60 - i * 10) for i in range(6)]
    events.sort(key=lambda e: e.occurred_at)
    participants = []
    for i, e in enumerate(events):
        participants.append(_winner(e.id, winners_cycle[i]))
        participants.append(_buyer(e.id, buyer_id))

    session = _FakeAsyncSession([events, participants])
    signals = await T19BidRotationTypology().run(session)

    assert len(signals) == 1
    s = signals[0]
    assert s.severity in (SignalSeverity.CRITICAL, SignalSeverity.HIGH)
    assert s.factors["n_unique_winners"] == 3
    assert s.factors["catmat_group"] == "group_x"


@pytest.mark.asyncio
async def test_t19_signal_has_evidence_refs():
    """Signal includes evidence_refs pointing to event IDs."""
    buyer_id = uuid.uuid4()
    winner_a = uuid.uuid4()
    winner_b = uuid.uuid4()
    events = [_licitacao(days_ago=60 - i * 10) for i in range(6)]
    events.sort(key=lambda e: e.occurred_at)
    participants = []
    for i, e in enumerate(events):
        w = winner_a if i % 2 == 0 else winner_b
        participants.append(_winner(e.id, w))
        participants.append(_buyer(e.id, buyer_id))

    session = _FakeAsyncSession([events, participants])
    signals = await T19BidRotationTypology().run(session)

    assert len(signals) == 1
    s = signals[0]
    assert len(s.evidence_refs) > 0
    assert len(s.event_ids) > 0
    assert s.period_start is not None
    assert s.period_end is not None


# ---------------------------------------------------------------------------
# Boundary tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_t19_boundary_exactly_4_events():
    """Exactly 4 events with valid rotation → signal produced."""
    buyer_id = uuid.uuid4()
    winner_a = uuid.uuid4()
    winner_b = uuid.uuid4()
    # A B A B: entropy=2/4=0.5, alternation_rate=1.0
    events = [_licitacao(days_ago=40 - i * 10) for i in range(4)]
    events.sort(key=lambda e: e.occurred_at)
    participants = []
    for i, e in enumerate(events):
        w = winner_a if i % 2 == 0 else winner_b
        participants.append(_winner(e.id, w))
        participants.append(_buyer(e.id, buyer_id))

    session = _FakeAsyncSession([events, participants])
    signals = await T19BidRotationTypology().run(session)

    assert len(signals) == 1
    assert signals[0].severity == SignalSeverity.HIGH  # n_procs=4 < 6 → HIGH


@pytest.mark.asyncio
async def test_t19_boundary_entropy_at_lower_limit():
    """rotation_entropy exactly = 0.20 → signal produced.

    10 events, 2 unique winners → entropy = 2/10 = 0.20.
    Pattern: A B A B A B A B A B → alternation_rate = 1.0.
    """
    buyer_id = uuid.uuid4()
    winner_a = uuid.uuid4()
    winner_b = uuid.uuid4()
    events = [_licitacao(days_ago=100 - i * 10) for i in range(10)]
    events.sort(key=lambda e: e.occurred_at)
    participants = []
    for i, e in enumerate(events):
        w = winner_a if i % 2 == 0 else winner_b
        participants.append(_winner(e.id, w))
        participants.append(_buyer(e.id, buyer_id))

    session = _FakeAsyncSession([events, participants])
    signals = await T19BidRotationTypology().run(session)

    assert len(signals) == 1
    s = signals[0]
    assert abs(s.factors["rotation_entropy"] - 0.2) < 1e-9


@pytest.mark.asyncio
async def test_t19_boundary_entropy_near_upper_limit():
    """rotation_entropy near upper boundary (0.60) → signal produced.

    10 events, 6 unique winners → entropy = 6/10 = 0.60 (within [0.20, 0.65]).
    Alternate winners to keep alternation_rate = 1.0.
    Note: exact 0.65 is structurally impossible with n_unique<=6 constraint.
    """
    buyer_id = uuid.uuid4()
    all_winners = [uuid.uuid4() for _ in range(6)]
    events = [_licitacao(days_ago=100 - i * 10) for i in range(10)]
    events.sort(key=lambda e: e.occurred_at)
    participants = []
    for i, e in enumerate(events):
        w = all_winners[i % 6]
        participants.append(_winner(e.id, w))
        participants.append(_buyer(e.id, buyer_id))

    session = _FakeAsyncSession([events, participants])
    signals = await T19BidRotationTypology().run(session)

    assert len(signals) == 1
    s = signals[0]
    assert abs(s.factors["rotation_entropy"] - 0.6) < 1e-9


@pytest.mark.asyncio
async def test_t19_boundary_alternation_rate_exactly_05():
    """alternation_rate exactly = 0.5 → HIGH signal (boundary >=0.5 passes).

    6 events, sequence: A B A A B A
    Consecutive pairs: (A,B),(B,A),(A,A),(A,B),(B,A)
    Alternating: 4 out of 5 → rate = 0.8... Let's use a crafted sequence instead.

    We need exactly 0.5: 4 pairs, 2 alternating.
    Use 5 events: A B A A A → pairs: (A,B),(B,A),(A,A),(A,A) → 2/4=0.5.
    entropy = 2/5 = 0.4 → in range.
    """
    buyer_id = uuid.uuid4()
    winner_a = uuid.uuid4()
    winner_b = uuid.uuid4()
    events = [_licitacao(days_ago=50 - i * 10) for i in range(5)]
    events.sort(key=lambda e: e.occurred_at)
    # sequence: A B A A A
    winner_seq = [winner_a, winner_b, winner_a, winner_a, winner_a]
    participants = []
    for i, e in enumerate(events):
        participants.append(_winner(e.id, winner_seq[i]))
        participants.append(_buyer(e.id, buyer_id))

    session = _FakeAsyncSession([events, participants])
    signals = await T19BidRotationTypology().run(session)

    assert len(signals) == 1
    s = signals[0]
    assert s.severity == SignalSeverity.HIGH
    assert abs(s.factors["rotation_alternation_rate"] - 0.5) < 1e-9


@pytest.mark.asyncio
async def test_t19_boundary_n_unique_winners_exactly_6():
    """n_unique_winners = 6 (max allowed) → signal produced."""
    buyer_id = uuid.uuid4()
    all_winners = [uuid.uuid4() for _ in range(6)]
    # 12 events cycling through 6 winners: entropy = 6/12 = 0.5, alternation = 1.0
    events = [_licitacao(days_ago=120 - i * 10) for i in range(12)]
    events.sort(key=lambda e: e.occurred_at)
    participants = []
    for i, e in enumerate(events):
        participants.append(_winner(e.id, all_winners[i % 6]))
        participants.append(_buyer(e.id, buyer_id))

    session = _FakeAsyncSession([events, participants])
    signals = await T19BidRotationTypology().run(session)

    assert len(signals) == 1
    assert signals[0].factors["n_unique_winners"] == 6


@pytest.mark.asyncio
async def test_t19_boundary_n_unique_winners_7_skipped():
    """n_unique_winners = 7 (above max) → no signal."""
    buyer_id = uuid.uuid4()
    all_winners = [uuid.uuid4() for _ in range(7)]
    events = [_licitacao(days_ago=140 - i * 10) for i in range(14)]
    events.sort(key=lambda e: e.occurred_at)
    participants = []
    for i, e in enumerate(events):
        participants.append(_winner(e.id, all_winners[i % 7]))
        participants.append(_buyer(e.id, buyer_id))

    session = _FakeAsyncSession([events, participants])
    signals = await T19BidRotationTypology().run(session)

    assert signals == []


@pytest.mark.asyncio
async def test_t19_critical_threshold_6_procs_high_alternation():
    """n_procs=6 AND alternation_rate>=0.7 → CRITICAL severity."""
    buyer_id = uuid.uuid4()
    winner_a = uuid.uuid4()
    winner_b = uuid.uuid4()
    # A B A B A B: 6 events, alternation = 1.0, entropy = 0.33
    events = [_licitacao(days_ago=60 - i * 10) for i in range(6)]
    events.sort(key=lambda e: e.occurred_at)
    participants = []
    for i, e in enumerate(events):
        w = winner_a if i % 2 == 0 else winner_b
        participants.append(_winner(e.id, w))
        participants.append(_buyer(e.id, buyer_id))

    session = _FakeAsyncSession([events, participants])
    signals = await T19BidRotationTypology().run(session)

    assert len(signals) == 1
    assert signals[0].severity == SignalSeverity.CRITICAL


@pytest.mark.asyncio
async def test_t19_winner_sequence_capped_at_10():
    """winner_sequence in factors is capped at 10 entries.

    Use 6 winners cycling over 12 events: entropy=6/12=0.5, alternation=1.0.
    """
    buyer_id = uuid.uuid4()
    all_winners = [uuid.uuid4() for _ in range(6)]
    # 12 events → winner_sequence has 12 entries → capped at 10
    events = [_licitacao(days_ago=120 - i * 10) for i in range(12)]
    events.sort(key=lambda e: e.occurred_at)
    participants = []
    for i, e in enumerate(events):
        participants.append(_winner(e.id, all_winners[i % 6]))
        participants.append(_buyer(e.id, buyer_id))

    session = _FakeAsyncSession([events, participants])
    signals = await T19BidRotationTypology().run(session)

    assert len(signals) == 1
    assert len(signals[0].factors["winner_sequence"]) <= 10
