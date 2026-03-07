"""Tests for _watchdog_recover_orphans and its integration with pipeline_watchdog."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from worker.tasks import maintenance_tasks


class _FakeScalarsResult:
    def __init__(self, values):
        self._values = values

    def scalars(self):
        return self

    def all(self):
        return self._values


class _FakeScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


def _make_orphan(connector, job, minutes_ago=30):
    return SimpleNamespace(
        connector=connector,
        job=job,
        status="running",
        finished_at=None,
        created_at=datetime.now(timezone.utc) - timedelta(minutes=minutes_ago),
        errors=None,
    )


def _make_ingest_state(last_cursor=None):
    return SimpleNamespace(last_cursor=last_cursor)


def test_watchdog_recover_orphans_finalizes_and_redispatches(monkeypatch):
    """_watchdog_recover_orphans should finalize orphans >10min old and re-dispatch."""
    orphan = _make_orphan("portal_transparencia", "pt_despesas_execucao", minutes_ago=30)
    state = _make_ingest_state(last_cursor="w2p15")

    call_idx = {"n": 0}

    def _fake_execute(stmt):
        call_idx["n"] += 1
        if call_idx["n"] == 1:
            return _FakeScalarsResult([orphan])
        return _FakeScalarResult(state)

    session = MagicMock()
    session.execute = _fake_execute
    session.__enter__ = MagicMock(return_value=session)
    session.__exit__ = MagicMock(return_value=False)

    with patch("shared.db_sync.SyncSession", return_value=session), \
         patch("worker.tasks.ingest_tasks.ingest_connector") as mock_task:
        mock_task.apply_async = MagicMock()
        result = maintenance_tasks._watchdog_recover_orphans()

    assert result is not None
    assert result["status"] == "recovered_orphans"
    assert result["count"] == 1
    assert result["redispatched"] == 1
    assert orphan.status == "error"
    assert orphan.errors["auto_recovered"] is True


def test_watchdog_recover_orphans_returns_none_when_no_orphans(monkeypatch):
    """_watchdog_recover_orphans returns None when there are no orphans."""
    session = MagicMock()
    session.execute.return_value = _FakeScalarsResult([])
    session.__enter__ = MagicMock(return_value=session)
    session.__exit__ = MagicMock(return_value=False)

    with patch("shared.db_sync.SyncSession", return_value=session):
        result = maintenance_tasks._watchdog_recover_orphans()

    assert result is None


def test_watchdog_pipeline_skips_when_no_orphans_and_ingest_running(monkeypatch):
    """pipeline_watchdog proceeds to normal logic when _watchdog_recover_orphans returns None."""
    monkeypatch.setattr(maintenance_tasks, "_watchdog_recover_orphans", lambda: None)

    session = MagicMock()
    session.__enter__ = MagicMock(return_value=session)
    session.__exit__ = MagicMock(return_value=False)

    # First execute: ingest_running_count = 2
    result_mock = MagicMock()
    result_mock.scalar_one.return_value = 2
    session.execute.return_value = result_mock

    with patch("shared.db_sync.SyncSession", return_value=session):
        result = maintenance_tasks.pipeline_watchdog()

    assert result == {"status": "skip", "reason": "ingest_running"}


def test_watchdog_pipeline_returns_recovery_when_orphans_found(monkeypatch):
    """pipeline_watchdog returns early when _watchdog_recover_orphans finds orphans."""
    recovery_result = {"status": "recovered_orphans", "count": 3, "redispatched": 2}
    monkeypatch.setattr(maintenance_tasks, "_watchdog_recover_orphans", lambda: recovery_result)

    result = maintenance_tasks.pipeline_watchdog()

    assert result == recovery_result
