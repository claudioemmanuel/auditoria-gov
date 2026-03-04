from unittest.mock import MagicMock, patch


def test_trigger_post_ingest_recompute_importable():
    from worker.tasks.maintenance_tasks import trigger_post_ingest_recompute

    assert callable(trigger_post_ingest_recompute)


def test_trigger_post_ingest_recompute_dispatches_baselines_and_signals():
    from worker.tasks.maintenance_tasks import trigger_post_ingest_recompute

    baseline_mock = MagicMock()
    signal_mock = MagicMock()

    with (
        patch("worker.tasks.baseline_tasks.compute_all_baselines", baseline_mock),
        patch("worker.tasks.signal_tasks.run_all_signals", signal_mock),
    ):
        result = trigger_post_ingest_recompute(
            connector="portal_transparencia", job="pt_beneficios"
        )

    baseline_mock.apply_async.assert_called_once_with(queue="default")
    signal_mock.apply_async.assert_called_once_with(queue="signals")

    assert result["status"] == "dispatched"
    assert result["connector"] == "portal_transparencia"
    assert result["job"] == "pt_beneficios"


def test_trigger_post_ingest_recompute_idempotent():
    """Multiple calls are harmless — they just trigger extra recomputes."""
    from worker.tasks.maintenance_tasks import trigger_post_ingest_recompute

    baseline_mock = MagicMock()
    signal_mock = MagicMock()

    with (
        patch("worker.tasks.baseline_tasks.compute_all_baselines", baseline_mock),
        patch("worker.tasks.signal_tasks.run_all_signals", signal_mock),
    ):
        result1 = trigger_post_ingest_recompute(connector="senado", job="despesas")
        result2 = trigger_post_ingest_recompute(connector="senado", job="despesas")

    assert baseline_mock.apply_async.call_count == 2
    assert signal_mock.apply_async.call_count == 2
    assert result1["status"] == "dispatched"
    assert result2["status"] == "dispatched"
