"""Tests for auto-recovery of orphaned runs after worker restart."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, call, patch
import logging

from worker import worker_app


class _FakeRun:
    def __init__(self, connector, job, status="running", finished_at=None, created_at=None):
        self.connector = connector
        self.job = job
        self.status = status
        self.finished_at = finished_at
        self.created_at = created_at or datetime.now(timezone.utc) - timedelta(minutes=30)
        self.errors = None


class _FakeIngestState:
    def __init__(self, last_cursor=None):
        self.last_cursor = last_cursor


class _FakeScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _FakeScalarsResult:
    def __init__(self, values):
        self._values = values

    def scalars(self):
        return self

    def all(self):
        return self._values


def test_recover_orphaned_runs_finalizes_and_redispatches(monkeypatch):
    """Orphaned running runs are finalized as error and re-dispatched with cursor."""
    orphan = _FakeRun("portal_transparencia", "pt_despesas_execucao")
    state = _FakeIngestState(last_cursor="w3p42")

    call_count = {"n": 0}

    def _fake_execute(stmt):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _FakeScalarsResult([orphan])
        return _FakeScalarResult(state)

    session = MagicMock()
    session.execute = _fake_execute

    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=session)
    ctx.__exit__ = MagicMock(return_value=False)

    fake_sync_session = MagicMock(return_value=ctx)
    log = logging.getLogger("test_recovery")

    from sqlalchemy import select
    from shared.models.orm import RawRun, IngestState

    with patch.object(worker_app, "app") as mock_app:
        worker_app._recover_orphaned_runs(log, select, fake_sync_session, RawRun, IngestState)

        # Orphan should be finalized
        assert orphan.status == "error"
        assert orphan.finished_at is not None
        assert orphan.errors["auto_recovered"] is True
        session.commit.assert_called_once()

        # Should re-dispatch with saved cursor
        mock_app.send_task.assert_called_once()
        call_args = mock_app.send_task.call_args
        assert call_args[0][0] == "worker.tasks.ingest_tasks.ingest_connector"
        assert call_args[1]["args"] == ["portal_transparencia", "pt_despesas_execucao", "w3p42"]
        assert call_args[1]["queue"] == "ingest"


def test_recover_orphaned_runs_noop_when_no_orphans(monkeypatch):
    """No action when there are no orphaned runs."""
    session = MagicMock()
    session.execute.return_value = _FakeScalarsResult([])

    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=session)
    ctx.__exit__ = MagicMock(return_value=False)

    fake_sync_session = MagicMock(return_value=ctx)
    log = logging.getLogger("test_recovery")

    from sqlalchemy import select
    from shared.models.orm import RawRun, IngestState

    with patch.object(worker_app, "app") as mock_app:
        worker_app._recover_orphaned_runs(log, select, fake_sync_session, RawRun, IngestState)
        mock_app.send_task.assert_not_called()
        session.commit.assert_not_called()


def test_recover_orphaned_runs_respects_max_concurrent(monkeypatch):
    """At most 4 jobs are re-dispatched even if more orphans exist."""
    orphans = [
        _FakeRun(f"conn_{i}", f"job_{i}")
        for i in range(6)
    ]

    call_count = {"n": 0}

    def _fake_execute(stmt):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _FakeScalarsResult(orphans)
        return _FakeScalarResult(_FakeIngestState(last_cursor=None))

    session = MagicMock()
    session.execute = _fake_execute

    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=session)
    ctx.__exit__ = MagicMock(return_value=False)

    fake_sync_session = MagicMock(return_value=ctx)
    log = logging.getLogger("test_recovery")

    from sqlalchemy import select
    from shared.models.orm import RawRun, IngestState

    with patch.object(worker_app, "app") as mock_app:
        worker_app._recover_orphaned_runs(log, select, fake_sync_session, RawRun, IngestState)

        # All 6 orphans finalized
        assert all(o.status == "error" for o in orphans)

        # But only 4 re-dispatched
        assert mock_app.send_task.call_count == 4


def test_recover_orphaned_runs_deduplicates_same_job(monkeypatch):
    """Multiple orphans for the same (connector, job) pair are only re-dispatched once."""
    orphans = [
        _FakeRun("portal_transparencia", "pt_emendas"),
        _FakeRun("portal_transparencia", "pt_emendas"),
        _FakeRun("portal_transparencia", "pt_emendas"),
    ]

    call_count = {"n": 0}

    def _fake_execute(stmt):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _FakeScalarsResult(orphans)
        return _FakeScalarResult(_FakeIngestState(last_cursor="p10"))

    session = MagicMock()
    session.execute = _fake_execute

    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=session)
    ctx.__exit__ = MagicMock(return_value=False)

    fake_sync_session = MagicMock(return_value=ctx)
    log = logging.getLogger("test_recovery")

    from sqlalchemy import select
    from shared.models.orm import RawRun, IngestState

    with patch.object(worker_app, "app") as mock_app:
        worker_app._recover_orphaned_runs(log, select, fake_sync_session, RawRun, IngestState)

        # All 3 finalized
        assert all(o.status == "error" for o in orphans)

        # But only 1 re-dispatched
        assert mock_app.send_task.call_count == 1
