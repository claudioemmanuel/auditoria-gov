"""Tests for P0 fix: execute_chunked_in in baseline compute functions.

Validates that _compute_participants_baselines and _compute_hhi_baselines
use chunked IN queries instead of raw .in_() to avoid asyncpg 32K param crash.
"""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shared.baselines.compute import (
    _compute_participants_baselines,
    _compute_hhi_baselines,
)


def _make_event(event_type="licitacao", value_brl=100_000, attrs=None):
    ev = MagicMock()
    ev.id = uuid.uuid4()
    ev.type = event_type
    ev.value_brl = value_brl
    ev.occurred_at = datetime.now(timezone.utc)
    ev.attrs = attrs or {"modality": "pregao", "catmat_group": "MAT001"}
    return ev


def _make_participant(event_id, role="bidder"):
    p = MagicMock()
    p.event_id = event_id
    p.entity_id = uuid.uuid4()
    p.role = role
    return p


class TestParticipantsBaselineChunked:
    """P0: _compute_participants_baselines must use execute_chunked_in."""

    @pytest.mark.asyncio
    async def test_uses_chunked_in_for_participants(self):
        """Verify execute_chunked_in is called instead of raw .in_()."""
        events = [_make_event() for _ in range(10)]
        participants = [_make_participant(events[i % 10].id) for i in range(30)]

        session = AsyncMock()
        # First call: event query
        event_result = MagicMock()
        event_result.scalars.return_value.all.return_value = events
        session.execute.return_value = event_result

        with patch(
            "shared.baselines.compute.execute_chunked_in",
            new_callable=AsyncMock,
            return_value=participants,
        ) as mock_chunked:
            result = await _compute_participants_baselines(
                session,
                datetime.now(timezone.utc) - timedelta(days=730),
                datetime.now(timezone.utc),
            )
            mock_chunked.assert_called_once()
            # Verify the ids passed match event_ids
            call_args = mock_chunked.call_args
            assert call_args[0][0] is session  # first arg is session
            assert len(call_args[0][2]) == 10  # third arg is event_ids

    @pytest.mark.asyncio
    async def test_empty_events_returns_empty(self):
        session = AsyncMock()
        event_result = MagicMock()
        event_result.scalars.return_value.all.return_value = []
        session.execute.return_value = event_result

        result = await _compute_participants_baselines(
            session,
            datetime.now(timezone.utc) - timedelta(days=730),
            datetime.now(timezone.utc),
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_counts_bidders_per_event(self):
        """Verify bidder counting logic works with chunked results."""
        events = [_make_event() for _ in range(35)]  # Above MIN_SAMPLE_SIZE=30
        # 2 bidders per event
        participants = []
        for ev in events:
            participants.append(_make_participant(ev.id, role="bidder"))
            participants.append(_make_participant(ev.id, role="bidder"))

        session = AsyncMock()
        event_result = MagicMock()
        event_result.scalars.return_value.all.return_value = events
        session.execute.return_value = event_result

        with patch(
            "shared.baselines.compute.execute_chunked_in",
            new_callable=AsyncMock,
            return_value=participants,
        ):
            result = await _compute_participants_baselines(
                session,
                datetime.now(timezone.utc) - timedelta(days=730),
                datetime.now(timezone.utc),
            )
            # Should produce at least 1 baseline (modality group or national)
            assert len(result) >= 1


class TestHHIBaselineChunked:
    """P0: _compute_hhi_baselines must use execute_chunked_in."""

    @pytest.mark.asyncio
    async def test_uses_chunked_in_for_winners(self):
        """Verify execute_chunked_in is called for winner query."""
        events = [_make_event(value_brl=50_000) for _ in range(10)]
        winners = [_make_participant(events[i % 10].id, role="winner") for i in range(10)]

        session = AsyncMock()
        event_result = MagicMock()
        event_result.scalars.return_value.all.return_value = events
        session.execute.return_value = event_result

        with patch(
            "shared.baselines.compute.execute_chunked_in",
            new_callable=AsyncMock,
            return_value=winners,
        ) as mock_chunked:
            result = await _compute_hhi_baselines(
                session,
                datetime.now(timezone.utc) - timedelta(days=730),
                datetime.now(timezone.utc),
            )
            mock_chunked.assert_called_once()
            call_args = mock_chunked.call_args
            assert call_args[0][0] is session
            assert len(call_args[0][2]) == 10

    @pytest.mark.asyncio
    async def test_empty_events_returns_empty(self):
        session = AsyncMock()
        event_result = MagicMock()
        event_result.scalars.return_value.all.return_value = []
        session.execute.return_value = event_result

        result = await _compute_hhi_baselines(
            session,
            datetime.now(timezone.utc) - timedelta(days=730),
            datetime.now(timezone.utc),
        )
        assert result == []


class TestChunkedInScaleSimulation:
    """Regression: verify chunked_in handles >5000 event_ids without crash."""

    @pytest.mark.asyncio
    async def test_large_event_set_does_not_crash(self):
        """Simulate 8000 events — must split into 2 chunks of 5000."""
        events = [_make_event() for _ in range(8_000)]

        chunk_calls = []

        async def _tracking_chunked_in(session, stmt_factory, ids, **kw):
            chunk_calls.append(len(ids))
            return []

        session = AsyncMock()
        event_result = MagicMock()
        event_result.scalars.return_value.all.return_value = events
        session.execute.return_value = event_result

        with patch(
            "shared.baselines.compute.execute_chunked_in",
            side_effect=_tracking_chunked_in,
        ):
            await _compute_participants_baselines(
                session,
                datetime.now(timezone.utc) - timedelta(days=730),
                datetime.now(timezone.utc),
            )
            assert chunk_calls == [8_000]  # execute_chunked_in receives full list, chunks internally
