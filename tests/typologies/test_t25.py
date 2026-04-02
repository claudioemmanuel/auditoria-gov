"""Tests for T25 — TCU Condemned Entity x Active Contract typology."""
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from shared.models.signals import SignalSeverity
from shared.typologies.t25_tcu_condemned import T25TCUCondemnedTypology


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


# ── Fake ORM object factories ─────────────────────────────────────────────────


def _now():
    return datetime.now(timezone.utc)


def _sanction_event(
    *,
    entity_id,
    subtype="inidoneo",
    start_days_ago=365,
    end_days_from_now=365 * 5,
    indefinite=False,
):
    eid = uuid.uuid4()
    start = _now() - timedelta(days=start_days_ago)
    end = None if indefinite else (_now() + timedelta(days=end_days_from_now))
    event = SimpleNamespace(
        id=eid,
        type="sancao_tcu",
        attrs={
            "sanction_start": start.isoformat(),
            "sanction_end": end.isoformat() if end else None,
            "subtype": subtype,
        },
        occurred_at=start,
        description="TCU sanction",
        value_brl=None,
    )
    participant = SimpleNamespace(
        id=uuid.uuid4(),
        event_id=eid,
        entity_id=entity_id,
        role="sanctioned",
    )
    return event, participant


def _contract_event(
    *,
    entity_id,
    start_days_ago=30,
    end_days_from_now=335,
    value_brl=500_000.0,
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


# ── Zero-result cases ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_zero_no_sanctions():
    """No sancao_tcu events in DB → early exit, no signals."""
    session = _FakeSession([[]])
    signals = await T25TCUCondemnedTypology().run(session)
    assert signals == []


@pytest.mark.asyncio
async def test_zero_no_contracts():
    """Sanctions exist but no contrato events → no signals."""
    entity_id = uuid.uuid4()
    s, sp = _sanction_event(entity_id=entity_id)
    # Queue: sanctions, sanction_participants (via execute_chunked_in), contracts
    session = _FakeSession([[s], [sp], []])
    signals = await T25TCUCondemnedTypology().run(session)
    assert signals == []


@pytest.mark.asyncio
async def test_zero_no_matching_entity():
    """Sanctions and contracts exist but for different entities → no signals."""
    sanction_entity = uuid.uuid4()
    contract_entity = uuid.uuid4()  # different entity
    s, sp = _sanction_event(entity_id=sanction_entity)
    c, cp = _contract_event(entity_id=contract_entity)
    session = _FakeSession([[s], [sp], [c], [cp]])
    signals = await T25TCUCondemnedTypology().run(session)
    assert signals == []


# ── Positive cases ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_critical_inidoneo_new_contract():
    """Contract signed AFTER inidoneo sanction start → CRITICAL signal."""
    entity_id = uuid.uuid4()
    # Sanction: 365 days ago; contract: 30 days ago (after sanction → signed_during=True)
    s, sp = _sanction_event(entity_id=entity_id, subtype="inidoneo", start_days_ago=365)
    c, cp = _contract_event(entity_id=entity_id, start_days_ago=30)
    session = _FakeSession([[s], [sp], [c], [cp]])

    signals = await T25TCUCondemnedTypology().run(session)

    assert len(signals) == 1
    sig = signals[0]
    assert sig.severity == SignalSeverity.CRITICAL
    assert sig.typology_code == "T25"
    assert sig.factors["subtype"] == "inidoneo"
    assert sig.factors["signed_during_sanction"] is True
    assert sig.confidence == 0.97


@pytest.mark.asyncio
async def test_high_preexisting_contract():
    """Pre-existing contract that overlaps sanction window → HIGH signal."""
    entity_id = uuid.uuid4()
    # Sanction: started 30 days ago; contract: started 365 days ago (before sanction)
    s, sp = _sanction_event(entity_id=entity_id, subtype="inidoneo", start_days_ago=30)
    c, cp = _contract_event(entity_id=entity_id, start_days_ago=365, end_days_from_now=335)
    session = _FakeSession([[s], [sp], [c], [cp]])

    signals = await T25TCUCondemnedTypology().run(session)

    assert len(signals) == 1
    sig = signals[0]
    assert sig.severity == SignalSeverity.HIGH
    assert sig.factors["signed_during_sanction"] is False
    assert sig.confidence == 0.90


@pytest.mark.asyncio
async def test_medium_inabilitado_new_contract():
    """Contract signed AFTER inabilitado sanction → MEDIUM signal."""
    entity_id = uuid.uuid4()
    s, sp = _sanction_event(entity_id=entity_id, subtype="inabilitado", start_days_ago=365)
    c, cp = _contract_event(entity_id=entity_id, start_days_ago=30)
    session = _FakeSession([[s], [sp], [c], [cp]])

    signals = await T25TCUCondemnedTypology().run(session)

    assert len(signals) == 1
    sig = signals[0]
    assert sig.severity == SignalSeverity.MEDIUM
    assert sig.factors["subtype"] == "inabilitado"
    assert sig.factors["signed_during_sanction"] is True
    assert sig.confidence == 0.80


@pytest.mark.asyncio
async def test_no_signal_before_sanction():
    """Contract ended before sanction started — no temporal overlap → no signal."""
    entity_id = uuid.uuid4()
    # Sanction started 30 days ago; contract ended 60 days ago (no overlap)
    s, sp = _sanction_event(entity_id=entity_id, subtype="inidoneo", start_days_ago=30)
    c, cp = _contract_event(
        entity_id=entity_id,
        start_days_ago=200,
        end_days_from_now=-60,  # ended 60 days ago, well before sanction start
    )
    session = _FakeSession([[s], [sp], [c], [cp]])

    signals = await T25TCUCondemnedTypology().run(session)
    assert signals == []


@pytest.mark.asyncio
async def test_indefinite_sanction_overlap():
    """Sanction with null data_final (ongoing/indefinite) + active contract → CRITICAL."""
    entity_id = uuid.uuid4()
    # Indefinite sanction (no end date) — contract signed after sanction started
    s, sp = _sanction_event(
        entity_id=entity_id, subtype="inidoneo", start_days_ago=365, indefinite=True
    )
    c, cp = _contract_event(entity_id=entity_id, start_days_ago=30)
    session = _FakeSession([[s], [sp], [c], [cp]])

    signals = await T25TCUCondemnedTypology().run(session)

    assert len(signals) == 1
    sig = signals[0]
    assert sig.severity == SignalSeverity.CRITICAL
    assert sig.factors["signed_during_sanction"] is True


# ── Metadata ──────────────────────────────────────────────────────────────────


def test_t25_metadata():
    t = T25TCUCondemnedTypology()
    assert t.id == "T25"
    assert "TCU" in t.name
    assert "sancao_tcu" in t.required_domains
    assert "contrato" in t.required_domains
    assert "fraude_licitatoria" in t.corruption_types
    assert t.evidence_level == "direct"
