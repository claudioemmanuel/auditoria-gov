from unittest.mock import MagicMock

from shared.connectors.base import JobSpec
from worker.tasks import ingest_tasks


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
