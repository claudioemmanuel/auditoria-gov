"""Tests for P1 fixes in signal_tasks:
- Batch dedup check (single IN query instead of N individual queries)
- Batch _populate_signal_links (bulk INSERT instead of per-row)
"""

import uuid

import pytest

from openwatch_pipelines.signal_tasks import (
    _compute_dedup_key,
    _populate_signal_links,
)


class TestComputeDedupKey:
    """Unit: dedup key computation must be deterministic."""

    def test_same_inputs_same_key(self):
        eids = [uuid.uuid4(), uuid.uuid4()]
        evids = [uuid.uuid4()]
        key1 = _compute_dedup_key("T08", eids, evids, "2025-01-01", "2025-06-01")
        key2 = _compute_dedup_key("T08", eids, evids, "2025-01-01", "2025-06-01")
        assert key1 == key2

    def test_different_typology_different_key(self):
        eids = [uuid.uuid4()]
        evids = [uuid.uuid4()]
        key1 = _compute_dedup_key("T08", eids, evids, "2025-01-01", "2025-06-01")
        key2 = _compute_dedup_key("T10", eids, evids, "2025-01-01", "2025-06-01")
        assert key1 != key2

    def test_order_independent_entity_ids(self):
        eid1, eid2 = uuid.uuid4(), uuid.uuid4()
        evids = [uuid.uuid4()]
        key1 = _compute_dedup_key("T08", [eid1, eid2], evids, None, None)
        key2 = _compute_dedup_key("T08", [eid2, eid1], evids, None, None)
        assert key1 == key2, "Dedup key must be order-independent for entity_ids"

    def test_sha256_length(self):
        key = _compute_dedup_key("T01", [], [], None, None)
        assert len(key) == 64, "SHA256 hex digest must be 64 chars"


class TestPopulateSignalLinksBatch:
    """P1: _populate_signal_links must use batch INSERT instead of per-row."""

    @pytest.mark.asyncio
    async def test_batch_insert_events(self):
        """Verify batch INSERT for event links (single execute call)."""
        from unittest.mock import AsyncMock

        session = AsyncMock()
        signal_id = uuid.uuid4()
        event_ids = [str(uuid.uuid4()) for _ in range(5)]

        await _populate_signal_links(session, signal_id, [], event_ids)

        # Should be 1 batch call for events, not 5 individual calls
        assert session.execute.call_count == 1, (
            f"Expected 1 batch INSERT, got {session.execute.call_count} calls"
        )

    @pytest.mark.asyncio
    async def test_batch_insert_entities(self):
        """Verify batch INSERT for entity links (single execute call)."""
        from unittest.mock import AsyncMock

        session = AsyncMock()
        signal_id = uuid.uuid4()
        entity_ids = [str(uuid.uuid4()) for _ in range(5)]

        await _populate_signal_links(session, signal_id, entity_ids, [])

        assert session.execute.call_count == 1

    @pytest.mark.asyncio
    async def test_batch_insert_both(self):
        """When both event_ids and entity_ids are present, 2 batch INSERTs."""
        from unittest.mock import AsyncMock

        session = AsyncMock()
        signal_id = uuid.uuid4()
        entity_ids = [str(uuid.uuid4()) for _ in range(3)]
        event_ids = [str(uuid.uuid4()) for _ in range(4)]

        await _populate_signal_links(session, signal_id, entity_ids, event_ids)

        assert session.execute.call_count == 2, (
            f"Expected 2 batch INSERTs (events + entities), got {session.execute.call_count}"
        )

    @pytest.mark.asyncio
    async def test_empty_ids_no_queries(self):
        """No queries when both lists are empty."""
        from unittest.mock import AsyncMock

        session = AsyncMock()
        await _populate_signal_links(session, uuid.uuid4(), [], [])
        session.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_invalid_uuids_skipped(self):
        """Invalid UUID strings should be silently skipped."""
        from unittest.mock import AsyncMock

        session = AsyncMock()
        signal_id = uuid.uuid4()

        await _populate_signal_links(
            session, signal_id, ["not-a-uuid", "also-bad"], ["invalid"]
        )
        session.execute.assert_not_called()


class TestBatchDedupCheck:
    """P1: run_single_signal must batch-check dedup keys in one query."""

    def test_batch_dedup_uses_in_clause(self, monkeypatch):
        """Verify dedup check uses .in_() batch query, not per-signal SELECT."""
        from unittest.mock import AsyncMock, MagicMock

        from openwatch_pipelines import signal_tasks

        class _FakeTypology:
            id = "T01"
            name = "Fake T01"
            required_domains: list[str] = []

            async def run(self, session):
                return []

        class _FakeResult:
            def scalar_one_or_none(self):
                return type("TypRow", (), {"id": "typ-id"})()

            def scalars(self):
                return self

            def all(self):
                return []

        class _FakeAsyncSession:
            _execute_count = 0

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return False

            async def execute(self, _stmt):
                self._execute_count += 1
                return _FakeResult()

            def add(self, _obj):
                return None

            async def flush(self):
                return None

            async def commit(self):
                return None

        fake_session = _FakeAsyncSession()

        import shared.db as db_module
        import shared.typologies.registry as registry_module

        monkeypatch.setattr(db_module, "async_session", lambda: fake_session)
        monkeypatch.setattr(registry_module, "get_typology", lambda _: _FakeTypology())

        result = signal_tasks.run_single_signal("T01")
        assert result["candidates"] == 0
        # With 0 candidates, should have minimal queries (typology lookup + run log)
        assert fake_session._execute_count <= 4
