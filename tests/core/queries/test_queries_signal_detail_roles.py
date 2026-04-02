import uuid
from types import SimpleNamespace

import pytest

from openwatch_queries import queries


class _ExecResult:
    def __init__(self, *, scalar=None, scalar_values=None, rows=None):
        self._scalar = scalar
        self._scalar_values = scalar_values or []
        self._rows = rows or []

    def scalar_one_or_none(self):
        return self._scalar

    def scalars(self):
        return self

    def all(self):
        if self._rows:
            return self._rows
        return self._scalar_values


@pytest.mark.asyncio
async def test_get_signal_detail_filters_roles_to_signal_events(monkeypatch):
    signal_id = uuid.uuid4()
    entity_id = uuid.uuid4()
    event_id = uuid.uuid4()

    signal = SimpleNamespace(
        id=signal_id,
        typology=SimpleNamespace(code="T03", name="Fracionamento de Despesa"),
        severity="critical",
        data_completeness=0.91,
        title="Possível fracionamento — unknown",
        summary="Resumo",
        explanation_md=None,
        completeness_score=0.93,
        completeness_status="sufficient",
        factors={},
        evidence_refs=[],
        entity_ids=[str(entity_id)],
        event_ids=[str(event_id)],
        period_start=None,
        period_end=None,
        evidence_package_id=None,
        created_at=None,
    )

    async def _fake_get_signal_by_id(_session, _signal_id):
        return signal

    monkeypatch.setattr(queries, "get_signal_by_id", _fake_get_signal_by_id)

    class _FakeSession:
        def __init__(self):
            self._calls = 0

        async def execute(self, stmt):
            self._calls += 1

            if self._calls == 1:
                # Case lookup
                return _ExecResult(scalar=None)

            if self._calls == 2:
                # Entity lookup
                entity = SimpleNamespace(
                    id=entity_id,
                    type="org",
                    name="Prefeitura Municipal de Andradas",
                    identifiers={"uasg": "33479"},
                )
                return _ExecResult(scalar_values=[entity])

            if self._calls == 3:
                # Role aggregation must be constrained to signal.event_ids
                assert "event_participant.event_id" in str(stmt)
                row = SimpleNamespace(entity_id=entity_id, role="buyer", cnt=1)
                return _ExecResult(rows=[row])

            raise AssertionError("Unexpected execute() call")

    detail = await queries.get_signal_detail(_FakeSession(), signal_id)

    assert detail is not None
    assert detail["entities"][0]["roles"] == ["buyer"]


@pytest.mark.asyncio
async def test_get_signal_detail_with_no_event_ids_does_not_count_global_roles(monkeypatch):
    signal_id = uuid.uuid4()
    entity_id = uuid.uuid4()

    signal = SimpleNamespace(
        id=signal_id,
        typology=SimpleNamespace(code="T03", name="Fracionamento de Despesa"),
        severity="critical",
        data_completeness=0.91,
        title="Possível fracionamento — unknown",
        summary="Resumo",
        explanation_md=None,
        completeness_score=0.93,
        completeness_status="sufficient",
        factors={},
        evidence_refs=[],
        entity_ids=[str(entity_id)],
        event_ids=[],
        period_start=None,
        period_end=None,
        evidence_package_id=None,
        created_at=None,
    )

    async def _fake_get_signal_by_id(_session, _signal_id):
        return signal

    monkeypatch.setattr(queries, "get_signal_by_id", _fake_get_signal_by_id)

    class _FakeSession:
        def __init__(self):
            self._calls = 0

        async def execute(self, stmt):
            self._calls += 1

            if self._calls == 1:
                return _ExecResult(scalar=None)
            if self._calls == 2:
                entity = SimpleNamespace(
                    id=entity_id,
                    type="org",
                    name="Prefeitura Municipal de Andradas",
                    identifiers={"uasg": "33479"},
                )
                return _ExecResult(scalar_values=[entity])
            if self._calls >= 3:
                raise AssertionError(f"Unexpected execute() call: {stmt}")

            raise AssertionError("Unexpected execute() call")

    detail = await queries.get_signal_detail(_FakeSession(), signal_id)

    assert detail is not None
    assert detail["entities"][0]["roles"] == []
    assert detail["entities"][0]["roles_detailed"] == []
