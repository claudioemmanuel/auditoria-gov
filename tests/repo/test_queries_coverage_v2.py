from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import uuid

import pytest

from shared.models.coverage import CoverageItem, CoverageMapItem, CoverageMapResponse
from shared.repo import queries


@pytest.mark.asyncio
async def test_get_coverage_v2_analytics_summarizes_items(monkeypatch):
    async def _fake_get_analytical_coverage(_session):
        return [
            {"typology_code": "T03", "apt": True, "signals_30d": 2},
            {"typology_code": "T10", "apt": False, "signals_30d": 0},
            {"typology_code": "T08", "apt": True, "signals_30d": 0},
        ]

    monkeypatch.setattr(queries, "get_analytical_coverage", _fake_get_analytical_coverage)

    payload = await queries.get_coverage_v2_analytics(session=None)

    assert payload["summary"]["total_typologies"] == 3
    assert payload["summary"]["apt_count"] == 2
    assert payload["summary"]["blocked_count"] == 1
    assert payload["summary"]["with_signals_30d"] == 1
    assert len(payload["items"]) == 3


@pytest.mark.asyncio
async def test_get_coverage_v2_summary_marks_blocked_when_runtime_stuck(monkeypatch):
    now = datetime(2026, 3, 3, 12, 0, tzinfo=timezone.utc)

    async def _fake_get_coverage_list(_session):
        return [
            CoverageItem(
                connector="portal_transparencia",
                job="pt_emendas",
                domain="despesa",
                status="ok",
                enabled_in_mvp=True,
                freshness_lag_hours=2.0,
                total_items=100,
            )
        ]

    async def _fake_get_coverage_v2_analytics(_session):
        return {
            "summary": {"total_typologies": 1, "apt_count": 1, "blocked_count": 0, "with_signals_30d": 1},
            "items": [],
        }

    class _FakeSession:
        def __init__(self):
            self.calls = 0

        async def execute(self, _stmt):
            self.calls += 1
            if self.calls == 1:
                return _ExecResult(
                    rows=[
                        SimpleNamespace(
                            id=uuid.uuid4(),
                            connector="portal_transparencia",
                            job="pt_emendas",
                            status="running",
                            created_at=now - timedelta(minutes=40),
                            finished_at=None,
                            items_fetched=10,
                            items_normalized=0,
                            errors=None,
                        )
                    ]
                )
            if self.calls in {2, 3, 4, 5, 6}:
                return _ExecResult(rows=[0])
            return _ExecResult(rows=[])

    monkeypatch.setattr(queries, "get_coverage_list", _fake_get_coverage_list)
    monkeypatch.setattr(queries, "get_coverage_v2_analytics", _fake_get_coverage_v2_analytics)
    monkeypatch.setattr(queries, "_coverage_now_utc", lambda: now)

    payload = await queries.get_coverage_v2_summary(_FakeSession())

    assert payload["totals"]["runtime"]["stuck"] == 1
    assert payload["pipeline"]["overall_status"] == "blocked"


@pytest.mark.asyncio
async def test_get_coverage_v2_map_wraps_national_totals(monkeypatch):
    now = datetime(2026, 3, 3, 12, 0, tzinfo=timezone.utc)

    async def _fake_get_coverage_map(_session, layer="uf", metric="coverage", date_ref=None):
        return CoverageMapResponse(
            layer=layer,
            metric=metric,
            date_ref=now,
            generated_at=now,
            items=[
                CoverageMapItem(
                    code="SP",
                    label="SP",
                    layer="uf",
                    event_count=10,
                    signal_count=3,
                    coverage_score=1.0,
                    freshness_hours=2.0,
                    risk_score=0.8,
                    status="ok",
                ),
                CoverageMapItem(
                    code="MG",
                    label="MG",
                    layer="uf",
                    event_count=0,
                    signal_count=0,
                    coverage_score=0.0,
                    freshness_hours=None,
                    risk_score=0.0,
                    status="pending",
                ),
            ],
        )

    monkeypatch.setattr(queries, "get_coverage_map", _fake_get_coverage_map)

    payload = await queries.get_coverage_v2_map(session=None, layer="uf", metric="coverage")

    assert payload["national"]["regions_with_data"] == 1
    assert payload["national"]["regions_without_data"] == 1
    assert payload["national"]["total_events"] == 10
    assert payload["national"]["total_signals"] == 3
    assert len(payload["items"]) == 2


class _ExecResult:
    def __init__(self, rows=None):
        self._rows = rows or []

    def scalars(self):
        return self

    def all(self):
        return self._rows


@pytest.mark.asyncio
async def test_get_coverage_v2_sources_groups_by_connector(monkeypatch):
    now = datetime(2026, 3, 3, 15, 0, tzinfo=timezone.utc)

    async def _fake_get_coverage_list(_session):
        return [
            CoverageItem(
                connector="portal_transparencia",
                job="pt_emendas",
                domain="despesa",
                status="warning",
                enabled_in_mvp=True,
                freshness_lag_hours=30.0,
                total_items=100,
            ),
            CoverageItem(
                connector="portal_transparencia",
                job="pt_viagens",
                domain="despesa",
                status="ok",
                enabled_in_mvp=True,
                freshness_lag_hours=6.0,
                total_items=50,
            ),
            CoverageItem(
                connector="camara",
                job="camara_deputados",
                domain="pessoa",
                status="pending",
                enabled_in_mvp=True,
                freshness_lag_hours=None,
                total_items=0,
            ),
        ]

    class _FakeSession:
        async def execute(self, _stmt):
            return _ExecResult(
                rows=[
                    SimpleNamespace(
                        connector="portal_transparencia",
                        job="pt_emendas",
                        status="running",
                        created_at=now - timedelta(minutes=30),
                    ),
                    SimpleNamespace(
                        connector="portal_transparencia",
                        job="pt_viagens",
                        status="completed",
                        created_at=now - timedelta(minutes=10),
                    ),
                ]
            )

    monkeypatch.setattr(queries, "get_coverage_list", _fake_get_coverage_list)
    monkeypatch.setattr(queries, "_coverage_now_utc", lambda: now)

    payload = await queries.get_coverage_v2_sources(
        _FakeSession(),
        offset=0,
        limit=20,
    )

    assert payload["total"] == 2
    first = payload["items"][0]
    assert first["connector"] == "portal_transparencia"
    assert first["runtime"]["running_jobs"] == 1
    assert first["runtime"]["stuck_jobs"] == 1
    assert first["status_counts"]["warning"] == 1


@pytest.mark.asyncio
async def test_get_coverage_v2_run_detail_not_found_returns_none():
    run_id = uuid.uuid4()

    class _FakeSession:
        async def execute(self, _stmt):
            return _ExecResult(rows=[])

    payload = await queries.get_coverage_v2_run_detail(_FakeSession(), run_id)
    assert payload is None
