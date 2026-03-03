import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from shared.repo import queries


class _ExecResult:
    def __init__(self, *, scalar=None, rows=None):
        self._scalar = scalar
        self._rows = rows or []

    def scalar_one(self):
        return self._scalar

    def all(self):
        return self._rows


@pytest.mark.asyncio
async def test_get_radar_v2_summary_aggregates_counts():
    class _FakeSession:
        def __init__(self):
            self.calls = 0

        async def execute(self, _stmt):
            self.calls += 1
            if self.calls == 1:
                return _ExecResult(scalar=12)
            if self.calls == 2:
                return _ExecResult(
                    rows=[
                        SimpleNamespace(severity="critical", cnt=3),
                        SimpleNamespace(severity="high", cnt=9),
                    ]
                )
            if self.calls == 3:
                return _ExecResult(
                    rows=[
                        SimpleNamespace(code="T03", name="Fracionamento de Despesa", cnt=10),
                        SimpleNamespace(code="T10", name="Terceirizacao Paralela", cnt=2),
                    ]
                )
            if self.calls == 4:
                return _ExecResult(scalar=4)
            raise AssertionError("Unexpected execute call")

    summary = await queries.get_radar_v2_summary(
        _FakeSession(),
        typology_code="T03",
        severity="high",
    )

    assert summary.totals.signals == 12
    assert summary.totals.cases == 4
    assert summary.severity_counts.critical == 3
    assert summary.severity_counts.high == 9
    assert summary.typology_counts[0].code == "T03"
    assert summary.active_filters_count == 2


@pytest.mark.asyncio
async def test_get_radar_v2_signals_maps_event_and_entity_counts(monkeypatch):
    signal = SimpleNamespace(
        id=uuid.uuid4(),
        typology_code="T03",
        typology_name="Fracionamento de Despesa",
        severity="critical",
        confidence=0.91,
        title="Possivel fracionamento",
        summary="Resumo",
        period_start=None,
        period_end=None,
        created_at=datetime(2026, 3, 1, 10, 0, tzinfo=timezone.utc),
        event_ids=[uuid.uuid4(), uuid.uuid4()],
        entity_ids=[uuid.uuid4()],
    )

    async def _fake_get_signals_paginated(*_args, **_kwargs):
        return [signal], 1

    monkeypatch.setattr(queries, "get_signals_paginated", _fake_get_signals_paginated)

    items, total = await queries.get_radar_v2_signals(session=None)

    assert total == 1
    assert len(items) == 1
    assert items[0].event_count == 2
    assert items[0].entity_count == 1
    assert items[0].has_graph is True


@pytest.mark.asyncio
async def test_get_radar_v2_signal_preview_composes_sources(monkeypatch):
    signal_id = uuid.uuid4()

    async def _fake_get_signal_detail(*_args, **_kwargs):
        return {"id": str(signal_id), "title": "Sinal"}

    async def _fake_get_signal_graph(*_args, **_kwargs):
        return {"signal": {"id": str(signal_id)}}

    async def _fake_get_signal_evidence_page(*_args, **_kwargs):
        return {"signal_id": str(signal_id), "total": 7, "items": []}

    monkeypatch.setattr(queries, "get_signal_detail", _fake_get_signal_detail)
    monkeypatch.setattr(queries, "get_signal_graph", _fake_get_signal_graph)
    monkeypatch.setattr(queries, "get_signal_evidence_page", _fake_get_signal_evidence_page)

    preview = await queries.get_radar_v2_signal_preview(session=None, signal_id=signal_id)

    assert preview is not None
    assert preview["signal"]["id"] == str(signal_id)
    assert preview["graph"]["signal"]["id"] == str(signal_id)
    assert preview["evidence"]["total"] == 7


@pytest.mark.asyncio
async def test_get_radar_v2_coverage_summarizes_typologies(monkeypatch):
    async def _fake_get_analytical_coverage(_session):
        return [
            {"typology_code": "T03", "apt": True, "signals_30d": 2},
            {"typology_code": "T10", "apt": False, "signals_30d": 0},
        ]

    monkeypatch.setattr(queries, "get_analytical_coverage", _fake_get_analytical_coverage)

    payload = await queries.get_radar_v2_coverage(session=None)

    assert payload.summary.apt_count == 1
    assert payload.summary.blocked_count == 1
    assert payload.summary.with_signals_30d == 1
    assert payload.summary.total_typologies == 2
