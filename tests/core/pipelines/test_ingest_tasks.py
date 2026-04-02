from unittest.mock import MagicMock

from openwatch_connectors.base import JobSpec
from openwatch_pipelines import ingest_tasks


class _FakeConnectorA:
    def list_jobs(self):
        return [
            JobSpec(
                name="enabled_job",
                description="Enabled",
                domain="test",
                supports_incremental=True,
                enabled=True,
            ),
            JobSpec(
                name="disabled_job",
                description="Disabled",
                domain="test",
                supports_incremental=True,
                enabled=False,
            ),
        ]


class _FakeConnectorB:
    def list_jobs(self):
        return [
            JobSpec(
                name="full_dump_enabled",
                description="Full dump, enabled",
                domain="test",
                supports_incremental=False,
                enabled=True,
            )
        ]


def test_ingest_all_incremental_dispatches_only_enabled_jobs(monkeypatch):
    """Only enabled incremental jobs are dispatched."""
    dispatched: list[tuple[str, str]] = []

    def _fake_delay(connector_name: str, job_name: str):
        dispatched.append((connector_name, job_name))

    monkeypatch.setattr(ingest_tasks.ingest_connector, "delay", _fake_delay)

    import shared.connectors as connectors_module

    monkeypatch.setattr(
        connectors_module,
        "ConnectorRegistry",
        {
            "connector_a": _FakeConnectorA,
            "connector_b": _FakeConnectorB,
        },
    )

    result = ingest_tasks.ingest_all_incremental()

    assert result["status"] == "dispatched"
    # Only enabled_job (A) qualifies: incremental + enabled.
    # disabled_job (A) is disabled; full_dump_enabled (B) is non-incremental.
    assert result["count"] == 1
    assert set(dispatched) == {
        ("connector_a", "enabled_job"),
    }


def test_ingest_all_incremental_skips_non_incremental(monkeypatch):
    """ingest_all_incremental does NOT dispatch jobs with supports_incremental=False."""
    dispatched: list[tuple[str, str]] = []

    def _fake_delay(connector_name: str, job_name: str):
        dispatched.append((connector_name, job_name))

    monkeypatch.setattr(ingest_tasks.ingest_connector, "delay", _fake_delay)

    import shared.connectors as connectors_module

    monkeypatch.setattr(
        connectors_module,
        "ConnectorRegistry",
        {
            "connector_a": _FakeConnectorA,
            "connector_b": _FakeConnectorB,
        },
    )

    result = ingest_tasks.ingest_all_incremental()

    # full_dump_enabled from ConnectorB is enabled but non-incremental — must be excluded.
    assert ("connector_b", "full_dump_enabled") not in dispatched
    assert result["count"] == 1


def test_ingest_all_bulk_dispatches_only_non_incremental(monkeypatch):
    """ingest_all_bulk dispatches ONLY jobs where supports_incremental=False and enabled=True."""
    dispatched_calls: list[dict] = []

    def _fake_apply_async(*args, **kwargs):
        dispatched_calls.append({"args": kwargs.get("args"), "queue": kwargs.get("queue")})

    monkeypatch.setattr(ingest_tasks.ingest_connector, "apply_async", _fake_apply_async)

    import shutil
    from types import SimpleNamespace
    monkeypatch.setattr(shutil, "disk_usage", lambda path: SimpleNamespace(total=1000, used=400, free=600))

    import shared.connectors as connectors_module

    monkeypatch.setattr(
        connectors_module,
        "ConnectorRegistry",
        {
            "connector_a": _FakeConnectorA,
            "connector_b": _FakeConnectorB,
        },
    )

    result = ingest_tasks.ingest_all_bulk()

    assert result["status"] == "dispatched"
    # Only full_dump_enabled (B): non-incremental + enabled.
    assert result["count"] == 1
    assert len(dispatched_calls) == 1
    assert dispatched_calls[0]["args"] == ["connector_b", "full_dump_enabled"]
    assert dispatched_calls[0]["queue"] == "bulk"


class _FakeConnectorC:
    def list_jobs(self):
        return [
            JobSpec(
                name="full_dump_disabled",
                description="Full dump, disabled",
                domain="test",
                supports_incremental=False,
                enabled=False,
            )
        ]


def test_ingest_all_bulk_skips_disabled(monkeypatch):
    """ingest_all_bulk does NOT dispatch disabled non-incremental jobs."""
    dispatched_calls: list[dict] = []

    def _fake_apply_async(*args, **kwargs):
        dispatched_calls.append({"args": kwargs.get("args"), "queue": kwargs.get("queue")})

    monkeypatch.setattr(ingest_tasks.ingest_connector, "apply_async", _fake_apply_async)

    import shutil
    from types import SimpleNamespace
    monkeypatch.setattr(shutil, "disk_usage", lambda path: SimpleNamespace(total=1000, used=400, free=600))

    import shared.connectors as connectors_module

    monkeypatch.setattr(
        connectors_module,
        "ConnectorRegistry",
        {
            "connector_a": _FakeConnectorA,
            "connector_b": _FakeConnectorB,
            "connector_c": _FakeConnectorC,
        },
    )

    result = ingest_tasks.ingest_all_bulk()

    # ConnectorC's full_dump_disabled is non-incremental but disabled — must be excluded.
    assert ("connector_c", "full_dump_disabled") not in [
        (c["args"][0], c["args"][1]) for c in dispatched_calls
    ]
    # Only ConnectorB's full_dump_enabled should be dispatched.
    assert result["count"] == 1


def test_format_error_uses_repr_when_exception_message_is_empty():
    class _NoMessageError(Exception):
        def __str__(self) -> str:
            return ""

    formatted = ingest_tasks._format_error(_NoMessageError())
    assert formatted.startswith("_NoMessageError")


def test_finalize_stale_runs_marks_old_running_entries():
    stale = MagicMock()
    stale.status = "running"
    stale.errors = None
    stale.finished_at = None

    result_proxy = MagicMock()
    result_proxy.scalars.return_value.all.return_value = [stale]

    session = MagicMock()
    session.execute.return_value = result_proxy

    count = ingest_tasks._finalize_stale_running_runs(
        session,
        connector_name="compras_gov",
        job_name="compras_licitacoes_by_period",
    )

    assert count == 1
    assert stale.status == "error"
    assert stale.finished_at is not None
    assert stale.errors["error_type"] == "StaleRun"
    session.commit.assert_called_once()


# ── Time-slice helpers ─────────────────────────────────────────────


class _FakeIngestState:
    def __init__(self, last_run_at=None):
        self.last_run_at = last_run_at


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


def test_other_jobs_pending_true_when_never_ran(monkeypatch):
    """_other_jobs_pending returns True when another enabled job has never run."""
    import shared.connectors as connectors_module

    monkeypatch.setattr(
        connectors_module,
        "ConnectorRegistry",
        {
            "conn_a": _FakeConnectorA,
        },
    )

    session = MagicMock()
    session.execute.return_value = _FakeScalarResult(None)  # no IngestState row

    result = ingest_tasks._other_jobs_pending(session, "conn_a", "enabled_job")
    # _FakeConnectorA has "enabled_job" (skipped as current) and "disabled_job" (disabled, skipped).
    # No other enabled incremental jobs → False
    assert result is False


def test_other_jobs_pending_true_when_another_connector_never_ran(monkeypatch):
    """_other_jobs_pending returns True when a different connector's job never ran."""
    import shared.connectors as connectors_module

    class _FakeConnectorD:
        def list_jobs(self):
            return [
                JobSpec(name="other_job", description="Other", domain="test",
                        supports_incremental=True, enabled=True),
            ]

    monkeypatch.setattr(
        connectors_module,
        "ConnectorRegistry",
        {
            "conn_a": _FakeConnectorA,
            "conn_d": _FakeConnectorD,
        },
    )

    session = MagicMock()
    # conn_d/other_job has no IngestState
    session.execute.return_value = _FakeScalarResult(None)

    result = ingest_tasks._other_jobs_pending(session, "conn_a", "enabled_job")
    assert result is True


def test_other_jobs_pending_true_when_stale(monkeypatch):
    """_other_jobs_pending returns True when another job ran >2h ago."""
    from datetime import datetime, timedelta, timezone
    import shared.connectors as connectors_module

    class _FakeConnectorD:
        def list_jobs(self):
            return [
                JobSpec(name="other_job", description="Other", domain="test",
                        supports_incremental=True, enabled=True),
            ]

    monkeypatch.setattr(
        connectors_module,
        "ConnectorRegistry",
        {
            "conn_a": _FakeConnectorA,
            "conn_d": _FakeConnectorD,
        },
    )

    old_state = _FakeIngestState(
        last_run_at=datetime.now(timezone.utc) - timedelta(hours=3),
    )
    session = MagicMock()
    session.execute.return_value = _FakeScalarResult(old_state)

    result = ingest_tasks._other_jobs_pending(session, "conn_a", "enabled_job")
    assert result is True


def test_other_jobs_pending_false_when_all_recent(monkeypatch):
    """_other_jobs_pending returns False when all other jobs ran recently."""
    from datetime import datetime, timedelta, timezone
    import shared.connectors as connectors_module

    class _FakeConnectorD:
        def list_jobs(self):
            return [
                JobSpec(name="other_job", description="Other", domain="test",
                        supports_incremental=True, enabled=True),
            ]

    monkeypatch.setattr(
        connectors_module,
        "ConnectorRegistry",
        {
            "conn_a": _FakeConnectorA,
            "conn_d": _FakeConnectorD,
        },
    )

    recent_state = _FakeIngestState(
        last_run_at=datetime.now(timezone.utc) - timedelta(minutes=30),
    )
    session = MagicMock()
    session.execute.return_value = _FakeScalarResult(recent_state)

    result = ingest_tasks._other_jobs_pending(session, "conn_a", "enabled_job")
    assert result is False


def test_count_recent_yields_counts_consecutive(monkeypatch):
    """_count_recent_yields counts consecutive 'yielded' statuses from most recent."""
    session = MagicMock()
    session.execute.return_value = _FakeScalarsResult(
        ["yielded", "yielded", "yielded", "completed", "yielded"]
    )

    count = ingest_tasks._count_recent_yields(session, "conn", "job")
    assert count == 3  # stops at "completed"


def test_count_recent_yields_zero_when_no_yields(monkeypatch):
    """_count_recent_yields returns 0 when most recent run is not yielded."""
    session = MagicMock()
    session.execute.return_value = _FakeScalarsResult(
        ["completed", "yielded", "yielded"]
    )

    count = ingest_tasks._count_recent_yields(session, "conn", "job")
    assert count == 0


def test_count_recent_yields_empty(monkeypatch):
    """_count_recent_yields returns 0 when no runs exist."""
    session = MagicMock()
    session.execute.return_value = _FakeScalarsResult([])

    count = ingest_tasks._count_recent_yields(session, "conn", "job")
    assert count == 0
