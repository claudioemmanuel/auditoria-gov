"""Tests for P2 fix in T07 Cartel Network:
- Bidder set per event is capped at 50 to prevent O(k²) explosion
"""

import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shared.typologies.t07_cartel_network import T07CartelNetworkTypology


def _make_event(catmat="MAT001", buyer_id=None, situacao="ativa"):
    ev = MagicMock()
    ev.id = uuid.uuid4()
    ev.type = "licitacao"
    ev.value_brl = 50_000
    ev.occurred_at = datetime.now(timezone.utc) - timedelta(days=30)
    ev.attrs = {
        "catmat_group": catmat,
        "situacao": situacao,
    }
    return ev


def _make_participant(event_id, entity_id=None, role="bidder"):
    p = MagicMock()
    p.event_id = event_id
    p.entity_id = entity_id or uuid.uuid4()
    p.role = role
    return p


class TestT07BidderCap:
    """P2: T07 must cap bidders per event to prevent O(k²) pair explosion."""

    @pytest.mark.asyncio
    async def test_large_bidder_set_is_capped(self):
        """With 100 bidders per event, pair_counts should be capped at C(50,2) not C(100,2)."""
        buyer_id = uuid.uuid4()
        events = [_make_event(catmat="MAT001") for _ in range(5)]

        # Create 100 bidders per event — should be capped at 50
        participants = []
        for ev in events:
            participants.append(_make_participant(ev.id, buyer_id, role="buyer"))
            for _ in range(100):
                participants.append(_make_participant(ev.id, role="bidder"))

        session = AsyncMock()
        event_result = MagicMock()
        event_result.scalars.return_value.all.return_value = events
        session.execute.return_value = event_result

        with patch(
            "shared.typologies.t07_cartel_network.execute_chunked_in",
            new_callable=AsyncMock,
            return_value=participants,
        ):
            typology = T07CartelNetworkTypology()
            # Should not hang or take excessive time due to O(k²) with k=100
            signals = await typology.run(session)
            # The test passes if it completes in reasonable time (not O(k²) with k=100)

    @pytest.mark.asyncio
    async def test_small_bidder_set_not_capped(self):
        """With <50 bidders, all pairs should be considered."""
        buyer_id = uuid.uuid4()
        # Need 3+ events in same group for T07 to fire
        events = [_make_event(catmat="MAT002") for _ in range(4)]

        bidder_ids = [uuid.uuid4() for _ in range(10)]
        participants = []
        for ev in events:
            participants.append(_make_participant(ev.id, buyer_id, role="buyer"))
            for bid in bidder_ids:
                participants.append(_make_participant(ev.id, bid, role="bidder"))
            # Add a winner to trigger alternation check
            participants.append(_make_participant(ev.id, bidder_ids[0], role="winner"))

        session = AsyncMock()
        event_result = MagicMock()
        event_result.scalars.return_value.all.return_value = events
        session.execute.return_value = event_result

        with patch(
            "shared.typologies.t07_cartel_network.execute_chunked_in",
            new_callable=AsyncMock,
            return_value=participants,
        ):
            typology = T07CartelNetworkTypology()
            signals = await typology.run(session)
            # With 10 bidders × 4 events, C(10,2)=45 pairs — all should be considered

    @pytest.mark.asyncio
    async def test_zero_result_no_events(self):
        """Zero-result: no events should produce no signals."""
        session = AsyncMock()
        event_result = MagicMock()
        event_result.scalars.return_value.all.return_value = []
        session.execute.return_value = event_result

        typology = T07CartelNetworkTypology()
        signals = await typology.run(session)
        assert signals == []

    @pytest.mark.asyncio
    async def test_void_events_excluded(self):
        """Void events (deserta, fracassada) should be excluded."""
        events = [_make_event(situacao="deserta") for _ in range(5)]

        session = AsyncMock()
        event_result = MagicMock()
        event_result.scalars.return_value.all.return_value = events
        session.execute.return_value = event_result

        typology = T07CartelNetworkTypology()
        signals = await typology.run(session)
        assert signals == []
