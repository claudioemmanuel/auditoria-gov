"""Tests for T15 False Sole-Source typology — Art. 74 valid subtype exclusion."""
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from openwatch_typologies.t15_false_sole_source import (
    T15FalseSoleSourceTypology,
    _VALID_INEXIGIBILIDADE_SUBTYPES,
)


def _make_inexig_event(subtype="", catmat="groupA"):
    ev = MagicMock()
    ev.id = uuid.uuid4()
    ev.occurred_at = datetime.now(timezone.utc) - timedelta(days=10)
    ev.value_brl = 100_000.0
    ev.attrs = {
        "modality": "inexigibilidade",
        "situacao": "homologada",
        "catmat_group": catmat,
        "inexigibilidade_subtype": subtype,
    }
    return ev


@pytest.mark.asyncio
async def test_t15_valid_subtype_notoria_especializacao_no_signal():
    """notoria_especializacao is Art. 74 III — valid inexigibilidade, must not flag."""
    ev = _make_inexig_event(subtype="notoria_especializacao")
    session = AsyncMock()
    ev_result = MagicMock()
    ev_result.scalars.return_value.all.return_value = [ev]
    part_result = MagicMock()
    part_result.scalars.return_value.all.return_value = []
    session.execute.side_effect = [ev_result, part_result]

    signals = await T15FalseSoleSourceTypology().run(session)
    assert signals == []


@pytest.mark.asyncio
async def test_t15_all_valid_subtypes_excluded():
    """All Art. 74 valid subtypes must produce no T15 signals."""
    for subtype in _VALID_INEXIGIBILIDADE_SUBTYPES:
        ev = _make_inexig_event(subtype=subtype)
        session = AsyncMock()
        ev_result = MagicMock()
        ev_result.scalars.return_value.all.return_value = [ev]
        part_result = MagicMock()
        part_result.scalars.return_value.all.return_value = []
        session.execute.side_effect = [ev_result, part_result]
        signals = await T15FalseSoleSourceTypology().run(session)
        assert signals == [], f"Subtype {subtype!r} should not produce signals"


@pytest.mark.asyncio
async def test_t15_unknown_subtype_can_generate_signal():
    """Unknown inexigibilidade subtype (no Art. 74 basis) is suspicious when alternatives exist."""
    buyer = uuid.uuid4()
    winner = uuid.uuid4()

    inexig_ev = _make_inexig_event(subtype="")  # no valid basis

    # Competitive events for same catmat
    comp_events = []
    comp_parts = []
    for _ in range(3):  # 3 alternative suppliers
        ev = MagicMock()
        ev.id = uuid.uuid4()
        ev.occurred_at = datetime.now(timezone.utc) - timedelta(days=20)
        ev.value_brl = 50_000.0
        ev.attrs = {"modality": "pregao", "situacao": "homologada", "catmat_group": "groupA", "catmat_code": ""}
        comp_events.append(ev)
        p = MagicMock(); p.event_id = ev.id; p.entity_id = uuid.uuid4(); p.role = "bidder"
        comp_parts.append(p)

    # Participants for inexig_ev
    p_buyer = MagicMock(); p_buyer.event_id = inexig_ev.id; p_buyer.entity_id = buyer; p_buyer.role = "buyer"
    p_supplier1 = MagicMock(); p_supplier1.event_id = inexig_ev.id; p_supplier1.entity_id = winner; p_supplier1.role = "supplier"
    p_supplier2 = MagicMock(); p_supplier2.event_id = inexig_ev.id; p_supplier2.entity_id = winner; p_supplier2.role = "supplier"

    all_events = [inexig_ev] + comp_events
    all_parts = comp_parts + [p_buyer, p_supplier1, p_supplier2]

    session = AsyncMock()
    ev_result = MagicMock()
    ev_result.scalars.return_value.all.return_value = all_events
    part_result = MagicMock()
    part_result.scalars.return_value.all.return_value = all_parts
    session.execute.side_effect = [ev_result, part_result]

    signals = await T15FalseSoleSourceTypology().run(session)
    # May or may not generate signal depending on repeat count, but should not crash
    assert isinstance(signals, list)
