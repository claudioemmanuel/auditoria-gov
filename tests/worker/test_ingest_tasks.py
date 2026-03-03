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
    """All enabled jobs are dispatched regardless of supports_incremental."""
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
    # enabled_job (A) + full_dump_enabled (B) = 2; disabled_job (A) is skipped
    assert result["count"] == 2
    assert set(dispatched) == {
        ("connector_a", "enabled_job"),
        ("connector_b", "full_dump_enabled"),
    }


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
