"""Tests for T24 — Fraude em Cota ME/EPP (P5.1)."""
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from shared.typologies.t24_me_epp_quota_fraud import T24MeEppQuotaFraudTypology


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now():
    return datetime.now(timezone.utc)


def _event(
    etype="licitacao",
    occurred_at=None,
    value_brl=50_000.0,
    attrs=None,
    eid=None,
):
    return SimpleNamespace(
        id=eid or uuid.uuid4(),
        type=etype,
        occurred_at=occurred_at or _now() - timedelta(days=30),
        value_brl=value_brl,
        description="Licitacao teste",
        attrs=attrs or {},
    )


def _participant(event_id, entity_id, role="winner"):
    return SimpleNamespace(event_id=event_id, entity_id=entity_id, role=role)


def _entity(entity_id, porte="ME"):
    return SimpleNamespace(id=entity_id, attrs={"porte_empresa": porte})


def _make_session(events=(), participants=(), entities=()):
    """Fake async session returning pre-built lists in query order."""
    call_count = 0
    results = [events, participants, entities]

    async def execute(_stmt):
        nonlocal call_count
        data = results[call_count] if call_count < len(results) else []
        call_count += 1

        class _Scalars:
            def __init__(self, rows):
                self._rows = list(rows)
            def all(self):
                return self._rows

        class _Result:
            def __init__(self, rows):
                self._rows = rows
            def scalars(self):
                return _Scalars(self._rows)

        return _Result(data)

    session = AsyncMock()
    session.execute.side_effect = execute
    return session


# ── Zero-result cases ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_no_signals_when_no_exclusive_events():
    """No exclusive-lot events → early exit, no signals."""
    event = _event(attrs={})  # no me_epp_exclusive flag
    session = _make_session(events=[event])
    typology = T24MeEppQuotaFraudTypology()
    signals = await typology.run(session)
    assert signals == []


@pytest.mark.asyncio
async def test_no_signals_when_no_winners():
    """Exclusive lot event but no winner participants → no signals."""
    event = _event(attrs={"me_epp_exclusive": True})
    session = _make_session(
        events=[event],
        participants=[],  # no winners
        entities=[],
    )
    typology = T24MeEppQuotaFraudTypology()
    signals = await typology.run(session)
    assert signals == []


@pytest.mark.asyncio
async def test_no_signals_when_winner_is_legitimate_me():
    """ME-porte winner in exclusive lot → no signal (legitimate)."""
    eid = uuid.uuid4()
    entity_id = uuid.uuid4()
    event = _event(attrs={"me_epp_exclusive": True}, eid=eid)
    participant = _participant(eid, entity_id)
    entity = _entity(entity_id, porte="ME")
    session = _make_session(
        events=[event],
        participants=[participant],
        entities=[entity],
    )
    typology = T24MeEppQuotaFraudTypology()
    signals = await typology.run(session)
    assert signals == []


@pytest.mark.asyncio
async def test_no_signals_when_winner_is_epp():
    """EPP winner in exclusive lot → no signal."""
    eid = uuid.uuid4()
    entity_id = uuid.uuid4()
    event = _event(attrs={"cota_reservada_me_epp": True}, eid=eid)
    participant = _participant(eid, entity_id)
    entity = _entity(entity_id, porte="EPP")
    session = _make_session(
        events=[event],
        participants=[participant],
        entities=[entity],
    )
    typology = T24MeEppQuotaFraudTypology()
    signals = await typology.run(session)
    assert signals == []


# ── Positive cases ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_critical_signal_large_company_in_exclusive_lot():
    """GRANDE company wins ME/EPP exclusive lot → CRITICAL signal."""
    eid = uuid.uuid4()
    entity_id = uuid.uuid4()
    event = _event(attrs={"me_epp_exclusive": True}, eid=eid, value_brl=45_000.0)
    participant = _participant(eid, entity_id)
    entity = _entity(entity_id, porte="GRANDE")
    session = _make_session(
        events=[event],
        participants=[participant],
        entities=[entity],
    )
    typology = T24MeEppQuotaFraudTypology()
    signals = await typology.run(session)
    assert len(signals) == 1
    s = signals[0]
    assert s.severity.value == "critical"
    assert s.typology_code == "T24"
    assert s.factors["porte_empresa"] == "GRANDE"
    assert s.factors["me_epp_exclusive"] is True


@pytest.mark.asyncio
async def test_critical_signal_medio_company_cota_reservada():
    """MEDIO company wins cota_reservada_me_epp lot → CRITICAL signal."""
    eid = uuid.uuid4()
    entity_id = uuid.uuid4()
    event = _event(attrs={"cota_reservada_me_epp": True}, eid=eid)
    participant = _participant(eid, entity_id)
    entity = _entity(entity_id, porte="MEDIO")
    session = _make_session(
        events=[event],
        participants=[participant],
        entities=[entity],
    )
    typology = T24MeEppQuotaFraudTypology()
    signals = await typology.run(session)
    assert len(signals) == 1
    assert signals[0].severity.value == "critical"


@pytest.mark.asyncio
async def test_high_signal_fictitious_me_volume_pattern():
    """Same entity wins >= 3 exclusive lots in same organ in 12 months → HIGH signal."""
    entity_id = uuid.uuid4()
    orgao_cnpj = "12345678000100"
    base_date = _now() - timedelta(days=90)
    events = [
        _event(
            attrs={"me_epp_exclusive": True, "orgao_cnpj": orgao_cnpj},
            eid=uuid.uuid4(),
            occurred_at=base_date + timedelta(days=i * 15),
        )
        for i in range(3)
    ]
    participants = [_participant(e.id, entity_id) for e in events]
    entity = _entity(entity_id, porte="")  # unknown porte
    session = _make_session(
        events=events,
        participants=participants,
        entities=[entity],
    )
    typology = T24MeEppQuotaFraudTypology()
    signals = await typology.run(session)
    assert len(signals) >= 1
    high_signals = [s for s in signals if s.severity.value == "high"]
    assert len(high_signals) >= 1
    assert high_signals[0].factors["n_exclusive_lots_won"] == 3


# ── Edge/boundary case ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_no_high_signal_only_2_exclusive_lots():
    """Only 2 exclusive lots won → below threshold, no high signal."""
    entity_id = uuid.uuid4()
    orgao_cnpj = "12345678000100"
    base_date = _now() - timedelta(days=30)
    events = [
        _event(
            attrs={"me_epp_exclusive": True, "orgao_cnpj": orgao_cnpj},
            eid=uuid.uuid4(),
            occurred_at=base_date + timedelta(days=i * 10),
        )
        for i in range(2)
    ]
    participants = [_participant(e.id, entity_id) for e in events]
    entity = _entity(entity_id, porte="")
    session = _make_session(
        events=events,
        participants=participants,
        entities=[entity],
    )
    typology = T24MeEppQuotaFraudTypology()
    signals = await typology.run(session)
    high_signals = [s for s in signals if s.severity.value == "high"]
    assert len(high_signals) == 0


# ── Metadata ──────────────────────────────────────────────────────────────────

def test_t24_metadata():
    t = T24MeEppQuotaFraudTypology()
    assert t.id == "T24"
    assert "ME" in t.name or "EPP" in t.name
    assert "licitacao" in t.required_domains
    assert "fraude_licitatoria" in t.corruption_types
    assert t.evidence_level == "direct"
