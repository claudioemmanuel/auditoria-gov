import uuid
from types import SimpleNamespace

import pytest

from openwatch_queries import queries


class _ExecResult:
    def __init__(self, *, scalar=None, scalar_values=None):
        self._scalar = scalar
        self._scalar_values = scalar_values or []

    def scalar_one_or_none(self):
        return self._scalar

    def scalar_one(self):
        return self._scalar

    def scalars(self):
        return self

    def all(self):
        return self._scalar_values


@pytest.mark.asyncio
async def test_get_graph_neighborhood_returns_diagnostics_when_graph_missing():
    entity_id = uuid.uuid4()

    class _FakeSession:
        def __init__(self):
            self._calls = 0

        async def execute(self, _stmt):
            self._calls += 1
            if self._calls == 1:
                # center graph node lookup
                return _ExecResult(scalar=None)
            if self._calls == 2:
                # entity lookup for virtual center node
                return _ExecResult(
                    scalar=SimpleNamespace(
                        id=entity_id,
                        name="Prefeitura Municipal de Andradas",
                        type="org",
                    )
                )
            if self._calls == 3:
                # entity event count
                return _ExecResult(scalar=70)
            if self._calls == 4:
                # co-participant distinct count
                return _ExecResult(scalar=0)
            return _ExecResult(scalar_values=[])

    data = await queries.get_graph_neighborhood(_FakeSession(), entity_id, depth=1, limit=100)

    assert data.nodes == []
    assert data.edges == []
    assert data.diagnostics is not None
    assert data.diagnostics.graph_materialized is False
    assert data.virtual_center_node is not None
    assert data.virtual_center_node.entity_id == entity_id
