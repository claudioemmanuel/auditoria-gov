from unittest.mock import MagicMock, patch


def test_trigger_post_ingest_recompute_importable():
    from openwatch_pipelines.maintenance_tasks import trigger_post_ingest_recompute

    assert callable(trigger_post_ingest_recompute)


def test_trigger_post_ingest_recompute_dispatches_baselines_and_signals():
    from openwatch_pipelines.maintenance_tasks import trigger_post_ingest_recompute

    mock_result = MagicMock()
    mock_result.id = "test-chain-id-abc"
    mock_pipeline = MagicMock()
    mock_pipeline.apply_async.return_value = mock_result

    with patch("celery.chain", return_value=mock_pipeline):
        result = trigger_post_ingest_recompute(
            connector="portal_transparencia", job="pt_beneficios"
        )

    mock_pipeline.apply_async.assert_called_once()
    assert result["status"] == "dispatched"
    assert result["connector"] == "portal_transparencia"
    assert result["job"] == "pt_beneficios"
    assert "chain_id" in result


# ── Regression: run_full_pipeline ────────────────────────────────────────────
# Added to support automated pipeline orchestration: ER → baselines → signals.

def test_run_full_pipeline_dispatches_chain():
    from unittest.mock import MagicMock, patch
    from openwatch_pipelines.maintenance_tasks import run_full_pipeline

    mock_chain_result = MagicMock()
    mock_chain_result.id = "test-chain-id-123"

    mock_pipeline = MagicMock()
    mock_pipeline.apply_async.return_value = mock_chain_result

    # run_full_pipeline uses `from celery import chain, signature` inline
    with patch("celery.chain", return_value=mock_pipeline):
        result = run_full_pipeline()

    assert result["status"] == "dispatched"
    assert "chain_id" in result
    mock_pipeline.apply_async.assert_called_once()


def test_trigger_post_ingest_recompute_idempotent():
    """Multiple calls are harmless — they just trigger extra recomputes."""
    from openwatch_pipelines.maintenance_tasks import trigger_post_ingest_recompute

    mock_result = MagicMock()
    mock_result.id = "chain-id-idempotent"
    mock_pipeline = MagicMock()
    mock_pipeline.apply_async.return_value = mock_result

    with patch("celery.chain", return_value=mock_pipeline):
        result1 = trigger_post_ingest_recompute(connector="senado", job="despesas")
        result2 = trigger_post_ingest_recompute(connector="senado", job="despesas")

    assert mock_pipeline.apply_async.call_count == 2
    assert result1["status"] == "dispatched"
    assert result2["status"] == "dispatched"


# ── Regression: pipeline_watchdog ────────────────────────────────────────────
# The watchdog checks four conditions before dispatching the pipeline chain:
#   1. No active ingest runs (RawRun.status='running' count == 0)
#   2. No ER currently running (ERRunState.status='running' not found)
#   3. At least one completed ingest exists
#   4. ER watermark is older than the latest completed ingest
# If any condition fails → skip. If all pass → dispatch run_full_pipeline.

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch


def _make_session(*execute_returns):
    """Build a mock SyncSession that returns values in sequence per execute() call."""
    mock_session = MagicMock()
    mock_session.__enter__ = MagicMock(return_value=mock_session)
    mock_session.__exit__ = MagicMock(return_value=False)
    mock_session.execute.side_effect = list(execute_returns)
    return mock_session


_UNSET = object()


def _q(scalar_one=_UNSET, scalar_one_or_none=_UNSET):
    """Shorthand for a mock query result with a single return method."""
    m = MagicMock()
    if scalar_one is not _UNSET:
        m.scalar_one.return_value = scalar_one
    if scalar_one_or_none is not _UNSET:
        m.scalar_one_or_none.return_value = scalar_one_or_none
    return m


class TestPipelineWatchdog:
    def setup_method(self):
        from openwatch_pipelines.maintenance_tasks import pipeline_watchdog
        self.watchdog = pipeline_watchdog
        # Patch orphan recovery so it doesn't interfere with existing session mocks
        self._orphan_patcher = patch(
            "worker.tasks.maintenance_tasks._watchdog_recover_orphans", return_value=None
        )
        self._orphan_patcher.start()

    def teardown_method(self):
        self._orphan_patcher.stop()

    def test_skips_when_ingest_running(self):
        """Active ingest runs no longer cause an early skip — pipeline advances concurrently.
        Without a completed ingest, the watchdog skips with 'no_completed_ingest'."""
        session = _make_session(
            _q(scalar_one=3),              # ingest count = 3 (running)
            _q(scalar_one_or_none=None),   # no ER running
            _q(scalar_one=None),           # no completed ingest → skip
        )
        with patch("shared.db_sync.SyncSession", return_value=session):
            result = self.watchdog()
        assert result == {"status": "skip", "reason": "no_completed_ingest"}
        assert session.execute.call_count == 3

    def test_skips_when_er_running(self):
        """No active ingest but ER currently running → skip."""
        # Give the mock a real (recent) created_at so the stale-threshold
        # comparison doesn't raise TypeError.
        er_running_mock = MagicMock()
        er_running_mock.created_at = datetime.now(timezone.utc)
        session = _make_session(
            _q(scalar_one=0),                           # ingest count
            _q(scalar_one_or_none=er_running_mock),     # ER running (recent, not stale)
        )
        with patch("shared.db_sync.SyncSession", return_value=session):
            result = self.watchdog()
        assert result == {"status": "skip", "reason": "er_running"}

    def test_skips_when_no_completed_ingest(self):
        """No completed ingest at all → skip (nothing to process)."""
        session = _make_session(
            _q(scalar_one=0),          # ingest count
            _q(scalar_one_or_none=None),  # no ER running
            _q(scalar_one=None),       # last_ingest_at = None
        )
        with patch("shared.db_sync.SyncSession", return_value=session):
            result = self.watchdog()
        assert result == {"status": "skip", "reason": "no_completed_ingest"}

    def test_skips_when_er_up_to_date(self):
        """ER watermark >= last completed ingest → nothing new to process."""
        now = datetime.now(timezone.utc)
        ingest_at = now.replace(hour=1)
        watermark_at = now.replace(hour=2)  # ER ran AFTER ingest

        er_completed = MagicMock()
        er_completed.watermark_at = watermark_at

        session = _make_session(
            _q(scalar_one=0),              # ingest count
            _q(scalar_one_or_none=None),   # no ER running
            _q(scalar_one=ingest_at),      # last_ingest_at
            _q(scalar_one_or_none=er_completed),  # ER completed with recent watermark
            _q(scalar_one=0),              # procurement_count=0 → no baseline dispatch needed
            _q(scalar_one=0),              # baseline_count
        )
        with patch("shared.db_sync.SyncSession", return_value=session):
            result = self.watchdog()
        assert result == {"status": "skip", "reason": "er_up_to_date_no_procurement"}

    def test_dispatches_when_ingest_done_and_er_stale(self):
        """Ingest idle + ER watermark older than last ingest → dispatch pipeline."""
        now = datetime.now(timezone.utc)
        ingest_at = now.replace(hour=3)    # ingest finished recently
        watermark_at = now.replace(hour=1) # ER last ran before ingest

        er_completed = MagicMock()
        er_completed.watermark_at = watermark_at

        session = _make_session(
            _q(scalar_one=0),              # ingest count
            _q(scalar_one_or_none=None),   # no ER running
            _q(scalar_one=ingest_at),      # last_ingest_at
            _q(scalar_one_or_none=er_completed),  # stale ER watermark
            _q(scalar_one=0),              # procurement_count
            _q(scalar_one=0),              # baseline_count
            _q(scalar_one=0),              # backlog prediction: current_backlog count
        )

        mock_task_result = MagicMock()
        mock_task_result.id = "dispatched-task-id"
        mock_run_pipeline = MagicMock()
        mock_run_pipeline.apply_async.return_value = mock_task_result

        with (
            patch("shared.db_sync.SyncSession", return_value=session),
            patch("worker.tasks.maintenance_tasks.run_full_pipeline", mock_run_pipeline),
        ):
            result = self.watchdog()

        assert result["status"] == "dispatched"
        assert "task_id" in result
        mock_run_pipeline.apply_async.assert_called_once_with(queue="default")

    def test_dispatches_when_er_has_never_run(self):
        """No prior ER run (er_completed=None) + completed ingest → dispatch pipeline."""
        now = datetime.now(timezone.utc)

        session = _make_session(
            _q(scalar_one=0),              # ingest count
            _q(scalar_one_or_none=None),   # no ER running
            _q(scalar_one=now),            # last_ingest_at present
            _q(scalar_one_or_none=None),   # no completed ER ever
            _q(scalar_one=0),              # procurement_count
            _q(scalar_one=0),              # baseline_count
            _q(scalar_one=0),              # backlog prediction: current_backlog count
        )

        mock_task_result = MagicMock()
        mock_task_result.id = "first-run-task-id"
        mock_run_pipeline = MagicMock()
        mock_run_pipeline.apply_async.return_value = mock_task_result

        with (
            patch("shared.db_sync.SyncSession", return_value=session),
            patch("worker.tasks.maintenance_tasks.run_full_pipeline", mock_run_pipeline),
        ):
            result = self.watchdog()

        assert result["status"] == "dispatched"
        mock_run_pipeline.apply_async.assert_called_once_with(queue="default")
