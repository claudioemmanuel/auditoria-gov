import pytest

from openwatch_queries import queries


class _ExecResult:
    def __init__(self, scalar):
        self._scalar = scalar

    def scalar_one(self):
        return self._scalar


@pytest.mark.asyncio
async def test_get_signal_quality_metrics_includes_high_critical_explained_and_paginable_pct():
    # Total signals, high/critical, with explanation, high/critical explained+paginable,
    # with event_ids, with listed evidence, unknown titles
    values = iter([100, 40, 30, 24, 90, 80, 5])

    class _FakeSession:
        async def execute(self, _stmt):
            return _ExecResult(next(values))

    metrics = await queries.get_signal_quality_metrics(_FakeSession())

    assert metrics["total_signals"] == 100
    assert metrics["high_critical_signals"] == 40
    assert metrics["explanation_coverage_pct"] == 75.0
    assert metrics["evidence_paginable_pct"] == 90.0
    assert metrics["high_critical_explained_and_paginable_pct"] == 60.0
