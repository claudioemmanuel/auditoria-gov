"""Tests for P1 fix in T16 Budget Clientelism:
- HHI is pre-computed per relator once, not recalculated per event
"""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shared.typologies.t16_budget_clientelism import T16BudgetClientelismTypology


def _make_event(
    relator_id="REL001",
    value_brl=500_000,
    plano_registered=False,
    recipient_sanctioned=True,
    muni_revenue=100_000,
):
    ev = MagicMock()
    ev.id = uuid.uuid4()
    ev.type = "transferencia"
    ev.value_brl = value_brl
    ev.occurred_at = datetime.now(timezone.utc) - timedelta(days=30)
    ev.attrs = {
        "relator_id": relator_id,
        "plano_trabalho_registered": plano_registered,
        "recipient_sanctioned": recipient_sanctioned,
        "municipality_revenue_brl": muni_revenue,
    }
    return ev


def _make_participant(event_id, entity_id=None, role="beneficiary"):
    p = MagicMock()
    p.event_id = event_id
    p.entity_id = entity_id or uuid.uuid4()
    p.role = role
    return p


class TestT16HHICache:
    """P1: HHI must be pre-computed per relator, not recalculated per event."""

    @pytest.mark.asyncio
    async def test_hhi_computed_once_per_relator(self):
        """With N events from same relator, HHI should be computed once."""
        relator = "REL_UNIQUE_001"
        beneficiary_id = uuid.uuid4()

        # Create 100 events from same relator to same beneficiary
        # HHI = 1.0 (all goes to one beneficiary) → should trigger concentration flag
        events = [
            _make_event(
                relator_id=relator,
                plano_registered=False,
                recipient_sanctioned=True,
            )
            for _ in range(100)
        ]

        participants = []
        for ev in events:
            participants.append(_make_participant(ev.id, beneficiary_id, role="beneficiary"))

        session = AsyncMock()
        event_result = MagicMock()
        event_result.scalars.return_value.all.return_value = events
        session.execute.return_value = event_result

        with patch(
            "shared.typologies.t16_budget_clientelism.execute_chunked_in",
            new_callable=AsyncMock,
            return_value=participants,
        ):
            typology = T16BudgetClientelismTypology()
            signals = await typology.run(session)

            # With plano=False + sanctioned + HHI=1.0 → 3 flags → CRITICAL signals
            assert len(signals) == 100
            for sig in signals:
                assert sig.factors["relator_hhi"] == 1.0
                assert "relator_concentration" in sig.factors["flag_reasons"]

    @pytest.mark.asyncio
    async def test_zero_result_no_flags(self):
        """Events with no flags should produce no signals."""
        events = [
            _make_event(
                plano_registered=True,  # Not a flag
                recipient_sanctioned=False,  # Not a flag
                muni_revenue=10_000_000,  # Value << revenue, not a flag
                value_brl=1_000,
            )
        ]

        participants = [_make_participant(events[0].id)]

        session = AsyncMock()
        event_result = MagicMock()
        event_result.scalars.return_value.all.return_value = events
        session.execute.return_value = event_result

        with patch(
            "shared.typologies.t16_budget_clientelism.execute_chunked_in",
            new_callable=AsyncMock,
            return_value=participants,
        ):
            typology = T16BudgetClientelismTypology()
            signals = await typology.run(session)
            assert signals == []

    @pytest.mark.asyncio
    async def test_hhi_zero_for_diverse_relator(self):
        """Relator distributing to many beneficiaries → low HHI."""
        relator = "REL_DIVERSE"
        events = [
            _make_event(
                relator_id=relator,
                plano_registered=False,
                recipient_sanctioned=True,
                value_brl=100_000,
                muni_revenue=10_000,  # 10x ratio → flag
            )
            for _ in range(10)
        ]

        # Each event has a different beneficiary → HHI = 0.1
        participants = [
            _make_participant(ev.id, uuid.uuid4(), role="beneficiary")
            for ev in events
        ]

        session = AsyncMock()
        event_result = MagicMock()
        event_result.scalars.return_value.all.return_value = events
        session.execute.return_value = event_result

        with patch(
            "shared.typologies.t16_budget_clientelism.execute_chunked_in",
            new_callable=AsyncMock,
            return_value=participants,
        ):
            typology = T16BudgetClientelismTypology()
            signals = await typology.run(session)
            # With HHI=0.1 (< 0.7 threshold), no concentration flag
            for sig in signals:
                assert "relator_concentration" not in sig.factors["flag_reasons"]
                assert sig.factors["relator_hhi"] < _RELATOR_HHI_THRESHOLD


# Import threshold for assertion
from shared.typologies.t16_budget_clientelism import _RELATOR_HHI_THRESHOLD
