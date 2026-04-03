import uuid
from unittest.mock import MagicMock

import pytest

from shared.utils.query import (
    IN_CLAUSE_BATCH_SIZE,
    MAX_ASYNCPG_BIND_PARAMS,
    PARAMETER_HEADROOM,
    _dedupe_preserve_order,
    _effective_batch_size,
    execute_chunked_in,
)


def test_dedupe_preserve_order():
    a = uuid.uuid4()
    b = uuid.uuid4()
    c = uuid.uuid4()

    assert _dedupe_preserve_order([a, b, a, c, b]) == [a, b, c]


def test_effective_batch_size_respects_requested():
    assert _effective_batch_size(batch_size=1_000, params_per_id=1) == 1_000


def test_effective_batch_size_caps_by_parameter_budget():
    safe_budget = MAX_ASYNCPG_BIND_PARAMS - PARAMETER_HEADROOM
    expected = safe_budget // 2
    assert _effective_batch_size(batch_size=50_000, params_per_id=2) == expected


@pytest.mark.asyncio
async def test_execute_chunked_in_dedupes_ids_and_chunks():
    # 5 ids where one is duplicated -> 4 unique ids
    ids = [uuid.uuid4() for _ in range(4)]
    id_list = [ids[0], ids[1], ids[0], ids[2], ids[3]]

    calls = []

    class _FakeSession:
        async def execute(self, stmt):
            result = MagicMock()
            result.scalars.return_value.all.return_value = list(stmt)
            return result

    def _stmt_factory(batch):
        calls.append(list(batch))
        # return iterable payload so fake session can echo results
        return list(batch)

    results = await execute_chunked_in(
        _FakeSession(),
        _stmt_factory,
        id_list,
        batch_size=2,
        operation_name="test.chunk",
    )

    assert calls == [[ids[0], ids[1]], [ids[2], ids[3]]]
    assert results == [ids[0], ids[1], ids[2], ids[3]]


@pytest.mark.asyncio
async def test_execute_chunked_in_applies_param_bound():
    ids = [uuid.uuid4() for _ in range(4)]
    calls = []

    class _FakeSession:
        async def execute(self, stmt):
            result = MagicMock()
            result.scalars.return_value.all.return_value = []
            return result

    def _stmt_factory(batch):
        calls.append(list(batch))
        return []

    # With params_per_id near safe budget, effective batch size should collapse to 1.
    await execute_chunked_in(
        _FakeSession(),
        _stmt_factory,
        ids,
        batch_size=IN_CLAUSE_BATCH_SIZE,
        params_per_id=MAX_ASYNCPG_BIND_PARAMS - PARAMETER_HEADROOM,
        operation_name="test.param_bound",
    )

    assert len(calls) == 4
    assert all(len(c) == 1 for c in calls)


@pytest.mark.asyncio
async def test_execute_chunked_in_rejects_invalid_batch_size():
    with pytest.raises(ValueError, match="batch_size must be > 0"):
        await execute_chunked_in(
            session=MagicMock(),
            stmt_factory=lambda _: [],
            ids=[uuid.uuid4()],
            batch_size=0,
        )


@pytest.mark.asyncio
async def test_execute_chunked_in_rejects_invalid_params_per_id():
    with pytest.raises(ValueError, match="params_per_id must be > 0"):
        await execute_chunked_in(
            session=MagicMock(),
            stmt_factory=lambda _: [],
            ids=[uuid.uuid4()],
            params_per_id=0,
        )

