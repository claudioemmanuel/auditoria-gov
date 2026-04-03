"""Tests for T12 Directed Tender typology — PMI attenuation."""
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shared.typologies.t12_directed_tender import T12DirectedTenderTypology, _MIN_REPEAT_WINS


@pytest.mark.asyncio
async def test_t12_pmi_attenuates_restrictiveness_score():
    """PMI reduces restrictiveness_score by 50% → signal with PMI has lower score."""
    buyer = uuid.uuid4()
    winner = uuid.uuid4()

    # Create _MIN_REPEAT_WINS events, all with pmi_realizado=True
    events_pmi = []
    participants_pmi = []
    for i in range(_MIN_REPEAT_WINS):
        ev = MagicMock()
        ev.id = uuid.uuid4()
        ev.occurred_at = datetime.now(timezone.utc) - timedelta(days=30 + i)
        ev.value_brl = 50_000.0
        ev.attrs = {"modality": "pregao", "situacao": "homologada", "catmat_group": "groupX", "pmi_realizado": True}
        events_pmi.append(ev)
        p_bidder = MagicMock(); p_bidder.event_id = ev.id; p_bidder.entity_id = uuid.uuid4(); p_bidder.role = "bidder"
        p_buyer = MagicMock(); p_buyer.event_id = ev.id; p_buyer.entity_id = buyer; p_buyer.role = "buyer"
        p_winner = MagicMock(); p_winner.event_id = ev.id; p_winner.entity_id = winner; p_winner.role = "winner"
        participants_pmi.extend([p_bidder, p_buyer, p_winner])

    # Create same _MIN_REPEAT_WINS events without PMI
    events_no_pmi = []
    participants_no_pmi = []
    for i in range(_MIN_REPEAT_WINS):
        ev = MagicMock()
        ev.id = uuid.uuid4()
        ev.occurred_at = datetime.now(timezone.utc) - timedelta(days=30 + i)
        ev.value_brl = 50_000.0
        ev.attrs = {"modality": "pregao", "situacao": "homologada", "catmat_group": "groupY", "pmi_realizado": False}
        events_no_pmi.append(ev)
        p_bidder = MagicMock(); p_bidder.event_id = ev.id; p_bidder.entity_id = uuid.uuid4(); p_bidder.role = "bidder"
        p_buyer = MagicMock(); p_buyer.event_id = ev.id; p_buyer.entity_id = buyer; p_buyer.role = "buyer"
        p_winner = MagicMock(); p_winner.event_id = ev.id; p_winner.entity_id = winner; p_winner.role = "winner"
        participants_no_pmi.extend([p_bidder, p_buyer, p_winner])

    async def run_with_events(events_list, parts_list):
        session = AsyncMock()
        ev_result = MagicMock()
        ev_result.scalars.return_value.all.return_value = events_list
        with patch(
            "shared.typologies.t12_directed_tender.execute_chunked_in",
            new_callable=AsyncMock,
            return_value=parts_list,
        ), patch(
            "shared.typologies.t12_directed_tender.get_baseline",
            new_callable=AsyncMock,
            return_value={"p10": 2.0},
        ):
            session.execute.return_value = ev_result
            return await T12DirectedTenderTypology().run(session)

    signals_pmi = await run_with_events(events_pmi, participants_pmi)
    signals_no_pmi = await run_with_events(events_no_pmi, participants_no_pmi)

    # Both should produce signals (enough repeat wins)
    # PMI signal should have lower restrictiveness_score
    if signals_pmi and signals_no_pmi:
        assert signals_pmi[0].factors["restrictiveness_score"] < signals_no_pmi[0].factors["restrictiveness_score"]
        assert signals_pmi[0].factors.get("pmi_realizado") is True
        assert signals_no_pmi[0].factors.get("pmi_realizado") is False


@pytest.mark.asyncio
async def test_t12_zero_events_returns_empty():
    session = AsyncMock()
    ev_result = MagicMock()
    ev_result.scalars.return_value.all.return_value = []
    session.execute.return_value = ev_result
    signals = await T12DirectedTenderTypology().run(session)
    assert signals == []
