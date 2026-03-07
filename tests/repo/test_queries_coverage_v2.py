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
                            created_at=now - timedelta(minutes=130),
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
                        created_at=now - timedelta(minutes=130),
                        items_fetched=10,
                        items_normalized=5,
                        finished_at=None,
                        errors=None,
                    ),
                    SimpleNamespace(
                        connector="portal_transparencia",
                        job="pt_viagens",
                        status="completed",
                        created_at=now - timedelta(minutes=10),
                        items_fetched=20,
                        items_normalized=20,
                        finished_at=now - timedelta(minutes=5),
                        errors=None,
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


# ── Pipeline stage dependency tests ─────────────────────────────────────


def _make_er_state(status="completed"):
    return SimpleNamespace(status=status, created_at=datetime(2026, 3, 1, tzinfo=timezone.utc))


class _PipelineSession:
    """Fake async session that returns configurable counts for pipeline stage queries.

    The get_coverage_v2_summary function issues these queries in order:
      1. get_coverage_list (monkeypatched)
      2. _coverage_get_latest_runs (monkeypatched via session.execute for RawRun)
      3. get_coverage_v2_analytics (monkeypatched)
      4. session.execute(count Event)        → event_count
      5. session.execute(count GraphNode)     → graph_nodes
      6. session.execute(count GraphEdge)     → graph_edges
      7. session.execute(count Baseline)      → baseline_count
      8. session.execute(count RiskSignal)    → signal_count
      9. session.execute(select ERRunState)   → er_state
    """
    def __init__(
        self,
        event_count=100,
        graph_nodes=50,
        graph_edges=30,
        baseline_count=10,
        signal_count=5,
        er_state=None,
        latest_runs=None,
    ):
        self._counts = [event_count, graph_nodes, graph_edges, baseline_count, signal_count]
        self._er_state = er_state
        self._latest_runs = latest_runs or []
        self._call = 0

    async def execute(self, _stmt):
        self._call += 1
        # First call: latest runs query (from _coverage_get_latest_runs)
        if self._call == 1:
            return _ExecResult(rows=self._latest_runs)
        # Calls 2-6: scalar counts
        idx = self._call - 2
        if idx < len(self._counts):
            return _ExecResult(rows=[self._counts[idx]])
        # Call 7: ERRunState
        if self._er_state is not None:
            return _ExecResult(rows=[self._er_state])
        return _ExecResult(rows=[])


async def _run_pipeline_test(
    monkeypatch,
    coverage_items,
    event_count=100,
    graph_nodes=50,
    graph_edges=30,
    baseline_count=10,
    signal_count=5,
    er_state=None,
    latest_runs=None,
    runtime_running=0,
):
    """Helper to run get_coverage_v2_summary with controlled inputs."""
    now = datetime(2026, 3, 3, 12, 0, tzinfo=timezone.utc)

    async def _fake_get_coverage_list(_session):
        return coverage_items

    async def _fake_get_coverage_v2_analytics(_session):
        return {
            "summary": {"total_typologies": 1, "apt_count": 1, "blocked_count": 0, "with_signals_30d": 0},
            "items": [],
        }

    monkeypatch.setattr(queries, "get_coverage_list", _fake_get_coverage_list)
    monkeypatch.setattr(queries, "get_coverage_v2_analytics", _fake_get_coverage_v2_analytics)
    monkeypatch.setattr(queries, "_coverage_now_utc", lambda: now)

    # Build latest_runs from the runs list
    runs = latest_runs or []
    if runtime_running > 0 and not runs:
        runs = [
            SimpleNamespace(
                id=uuid.uuid4(),
                connector="portal_transparencia",
                job=f"running_job_{i}",
                status="running",
                created_at=now - timedelta(minutes=5),
                finished_at=None,
                items_fetched=10,
                items_normalized=0,
                errors=None,
            )
            for i in range(runtime_running)
        ]

    session = _PipelineSession(
        event_count=event_count,
        graph_nodes=graph_nodes,
        graph_edges=graph_edges,
        baseline_count=baseline_count,
        signal_count=signal_count,
        er_state=er_state,
        latest_runs=runs,
    )

    payload = await queries.get_coverage_v2_summary(session)
    stages = {s["code"]: s for s in payload["pipeline"]["stages"]}
    return payload, stages


@pytest.mark.asyncio
async def test_pipeline_all_up_to_date_when_healthy(monkeypatch):
    """When all data is present and nothing is processing, all stages should be up_to_date."""
    items = [
        CoverageItem(connector="pt", job="j1", domain="d", status="ok",
                      enabled_in_mvp=True, freshness_lag_hours=1.0, total_items=100),
    ]
    payload, stages = await _run_pipeline_test(
        monkeypatch,
        coverage_items=items,
        er_state=_make_er_state("completed"),
    )
    assert stages["ingest"]["status"] == "up_to_date"
    assert stages["entity_resolution"]["status"] == "up_to_date"
    assert stages["baselines"]["status"] == "up_to_date"
    assert stages["signals"]["status"] == "up_to_date"
    assert payload["pipeline"]["overall_status"] == "healthy"


@pytest.mark.asyncio
async def test_pipeline_signals_stale_when_ingest_processing(monkeypatch):
    """Signals must NOT be up_to_date while ingest is processing — should be stale."""
    items = [
        CoverageItem(connector="pt", job="j1", domain="d", status="ok",
                      enabled_in_mvp=True, freshness_lag_hours=1.0, total_items=100),
    ]
    _, stages = await _run_pipeline_test(
        monkeypatch,
        coverage_items=items,
        signal_count=10,
        er_state=_make_er_state("completed"),
        runtime_running=1,
    )
    assert stages["ingest"]["status"] == "processing"
    assert stages["signals"]["status"] == "stale"


@pytest.mark.asyncio
async def test_pipeline_er_stale_when_ingest_processing(monkeypatch):
    """ER stage should be stale when ingest is actively processing."""
    items = [
        CoverageItem(connector="pt", job="j1", domain="d", status="ok",
                      enabled_in_mvp=True, freshness_lag_hours=1.0, total_items=100),
    ]
    _, stages = await _run_pipeline_test(
        monkeypatch,
        coverage_items=items,
        er_state=_make_er_state("completed"),
        runtime_running=1,
    )
    assert stages["ingest"]["status"] == "processing"
    assert stages["entity_resolution"]["status"] == "stale"


@pytest.mark.asyncio
async def test_pipeline_baselines_stale_when_er_stale(monkeypatch):
    """Baselines should be stale when ER is stale (due to ingest processing)."""
    items = [
        CoverageItem(connector="pt", job="j1", domain="d", status="ok",
                      enabled_in_mvp=True, freshness_lag_hours=1.0, total_items=100),
    ]
    _, stages = await _run_pipeline_test(
        monkeypatch,
        coverage_items=items,
        baseline_count=5,
        er_state=_make_er_state("completed"),
        runtime_running=1,
    )
    assert stages["entity_resolution"]["status"] == "stale"
    assert stages["baselines"]["status"] == "stale"


@pytest.mark.asyncio
async def test_pipeline_downstream_pending_when_no_events(monkeypatch):
    """When there are no events, ER/baselines/signals should all be pending."""
    items = [
        CoverageItem(connector="pt", job="j1", domain="d", status="ok",
                      enabled_in_mvp=True, freshness_lag_hours=1.0, total_items=100),
    ]
    _, stages = await _run_pipeline_test(
        monkeypatch,
        coverage_items=items,
        event_count=0,
        graph_nodes=0,
        graph_edges=0,
        baseline_count=0,
        signal_count=0,
        er_state=None,
    )
    assert stages["entity_resolution"]["status"] == "pending"
    assert stages["baselines"]["status"] == "pending"
    assert stages["signals"]["status"] == "pending"


@pytest.mark.asyncio
async def test_pipeline_ingest_error_propagates_to_overall_blocked(monkeypatch):
    """When ingest has errors, overall_status should be 'blocked'."""
    items = [
        CoverageItem(connector="pt", job="j1", domain="d", status="error",
                      enabled_in_mvp=True, freshness_lag_hours=None, total_items=0),
    ]
    payload, stages = await _run_pipeline_test(
        monkeypatch,
        coverage_items=items,
        event_count=0,
        graph_nodes=0,
        graph_edges=0,
        baseline_count=0,
        signal_count=0,
        er_state=None,
    )
    assert stages["ingest"]["status"] == "error"
    assert payload["pipeline"]["overall_status"] == "blocked"


@pytest.mark.asyncio
async def test_pipeline_ingest_warning_when_stale_sources(monkeypatch):
    """When sources have stale data, ingest should show warning."""
    items = [
        CoverageItem(connector="pt", job="j1", domain="d", status="warning",
                      enabled_in_mvp=True, freshness_lag_hours=30.0, total_items=100),
    ]
    _, stages = await _run_pipeline_test(
        monkeypatch,
        coverage_items=items,
        er_state=_make_er_state("completed"),
    )
    assert stages["ingest"]["status"] == "warning"
    # ER should be stale since ingest is warning
    assert stages["entity_resolution"]["status"] == "stale"


@pytest.mark.asyncio
async def test_pipeline_er_pending_when_never_completed(monkeypatch):
    """ER stage should be pending when er_state has never completed."""
    items = [
        CoverageItem(connector="pt", job="j1", domain="d", status="ok",
                      enabled_in_mvp=True, freshness_lag_hours=1.0, total_items=100),
    ]
    _, stages = await _run_pipeline_test(
        monkeypatch,
        coverage_items=items,
        er_state=None,
    )
    assert stages["entity_resolution"]["status"] == "pending"


@pytest.mark.asyncio
async def test_pipeline_er_processing_when_running(monkeypatch):
    """ER stage should be processing when er_state is 'running'."""
    items = [
        CoverageItem(connector="pt", job="j1", domain="d", status="ok",
                      enabled_in_mvp=True, freshness_lag_hours=1.0, total_items=100),
    ]
    _, stages = await _run_pipeline_test(
        monkeypatch,
        coverage_items=items,
        er_state=_make_er_state("running"),
    )
    assert stages["entity_resolution"]["status"] == "processing"


@pytest.mark.asyncio
async def test_pipeline_overall_attention_when_any_stale(monkeypatch):
    """Overall status should be 'attention' when stages are stale but no errors."""
    items = [
        CoverageItem(connector="pt", job="j1", domain="d", status="ok",
                      enabled_in_mvp=True, freshness_lag_hours=1.0, total_items=100),
    ]
    payload, stages = await _run_pipeline_test(
        monkeypatch,
        coverage_items=items,
        er_state=_make_er_state("completed"),
        runtime_running=1,
    )
    assert stages["ingest"]["status"] == "processing"
    assert payload["pipeline"]["overall_status"] == "attention"


@pytest.mark.asyncio
async def test_pipeline_ingest_pending_when_no_items(monkeypatch):
    """When there are no coverage items, ingest should be pending."""
    payload, stages = await _run_pipeline_test(
        monkeypatch,
        coverage_items=[],
        event_count=0,
        graph_nodes=0,
        graph_edges=0,
        baseline_count=0,
        signal_count=0,
        er_state=None,
    )
    assert stages["ingest"]["status"] == "pending"
