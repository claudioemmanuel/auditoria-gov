"""Tests for T23 — Superfaturamento BIM stub (P5.2)."""
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from shared.typologies.t23_bim_cost_overrun import T23BimCostOverrunTypology


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now():
    return datetime.now(timezone.utc)


def _bim_event(
    sinapi_ref: float,
    contracted: float,
    obra_id: str = "obra-001",
    quantity: float = 10.0,
    value_brl: float | None = None,
    occurred_at=None,
):
    overrun_frac = max(0.0, (contracted - sinapi_ref) / sinapi_ref)
    return SimpleNamespace(
        id=uuid.uuid4(),
        type="orcamento_bim",
        occurred_at=occurred_at or _now() - timedelta(days=30),
        value_brl=value_brl or (contracted * quantity),
        attrs={
            "sinapi_reference_brl": sinapi_ref,
            "contracted_unit_price_brl": contracted,
            "quantity": quantity,
            "obra_id": obra_id,
        },
    )


def _make_session(events=()):
    call_count = 0

    async def execute(_stmt):
        nonlocal call_count
        call_count += 1

        class _Scalars:
            def all(self_):
                return list(events)

        class _Result:
            def scalars(self_):
                return _Scalars()

        return _Result()

    session = AsyncMock()
    session.execute.side_effect = execute
    return session


# ── Zero-result (stub / no data) ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_no_signals_when_no_bim_events():
    """No orcamento_bim events → stub returns [] (BIM data not loaded)."""
    session = _make_session(events=[])
    typology = T23BimCostOverrunTypology()
    signals = await typology.run(session)
    assert signals == []


@pytest.mark.asyncio
async def test_no_signals_when_overrun_below_threshold():
    """Items with overrun < 20% → not flagged."""
    events = [
        _bim_event(sinapi_ref=1000.0, contracted=1150.0)  # 15% — below threshold
        for _ in range(5)
    ]
    session = _make_session(events=events)
    typology = T23BimCostOverrunTypology()
    signals = await typology.run(session)
    assert signals == []


@pytest.mark.asyncio
async def test_no_signals_when_fewer_than_3_overrun_items():
    """Only 2 overrun items per obra → below minimum, no signal."""
    events = [
        _bim_event(sinapi_ref=1000.0, contracted=1500.0)  # 50% overrun
        for _ in range(2)
    ]
    session = _make_session(events=events)
    typology = T23BimCostOverrunTypology()
    signals = await typology.run(session)
    assert signals == []


# ── Positive cases ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_medium_signal_when_3_items_at_threshold():
    """3 items at exactly 25% overrun (above threshold) → MEDIUM signal."""
    events = [
        _bim_event(sinapi_ref=1000.0, contracted=1250.0, obra_id="obra-abc")
        for _ in range(3)
    ]
    session = _make_session(events=events)
    typology = T23BimCostOverrunTypology()
    signals = await typology.run(session)
    assert len(signals) == 1
    s = signals[0]
    assert s.severity.value == "medium"
    assert s.typology_code == "T23"
    assert s.factors["n_overrun_items"] == 3
    assert s.factors["obra_id"] == "obra-abc"


@pytest.mark.asyncio
async def test_high_signal_at_40pct_median_overrun():
    """3 items at 45% overrun (>=40%) → HIGH signal."""
    events = [
        _bim_event(sinapi_ref=1000.0, contracted=1450.0, obra_id="obra-xyz")
        for _ in range(4)
    ]
    session = _make_session(events=events)
    typology = T23BimCostOverrunTypology()
    signals = await typology.run(session)
    assert len(signals) == 1
    assert signals[0].severity.value == "high"


@pytest.mark.asyncio
async def test_critical_signal_at_80pct_median_overrun():
    """Items at 90% overrun (>=80%) → CRITICAL signal."""
    events = [
        _bim_event(sinapi_ref=1000.0, contracted=1900.0, obra_id="obra-crit")
        for _ in range(5)
    ]
    session = _make_session(events=events)
    typology = T23BimCostOverrunTypology()
    signals = await typology.run(session)
    assert len(signals) == 1
    assert signals[0].severity.value == "critical"


@pytest.mark.asyncio
async def test_signals_grouped_by_obra():
    """Two distinct obras, each with 3 overrun items → two signals."""
    events = (
        [_bim_event(sinapi_ref=1000.0, contracted=1300.0, obra_id="obra-1") for _ in range(3)] +
        [_bim_event(sinapi_ref=2000.0, contracted=2600.0, obra_id="obra-2") for _ in range(3)]
    )
    session = _make_session(events=events)
    typology = T23BimCostOverrunTypology()
    signals = await typology.run(session)
    assert len(signals) == 2
    obra_ids = {s.factors["obra_id"] for s in signals}
    assert obra_ids == {"obra-1", "obra-2"}


# ── Metadata ──────────────────────────────────────────────────────────────────

def test_t23_metadata():
    t = T23BimCostOverrunTypology()
    assert t.id == "T23"
    assert "BIM" in t.name or "Superfaturamento" in t.name
    assert "orcamento_bim" in t.required_domains
    assert "fraude_licitatoria" in t.corruption_types
    assert "peculato" in t.corruption_types
    assert t.evidence_level == "direct"
