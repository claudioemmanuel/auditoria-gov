from api.app.routers import internal


async def test_trigger_all_signals_dispatches_expected_task(monkeypatch):
    """E2E-style API-to-queue contract for all-signals trigger endpoint."""
    captured: dict[str, object] = {}

    class _FakeResult:
        id = "task-signals-123"

    class _FakeCelery:
        def send_task(self, task: str, args=None, queue: str | None = None):
            captured["task"] = task
            captured["args"] = args
            captured["queue"] = queue
            return _FakeResult()

    monkeypatch.setattr(internal, "celery_app", _FakeCelery())

    result = await internal.trigger_all_signals()

    assert result == {"status": "dispatched", "task_id": "task-signals-123"}
    assert captured == {
        "task": "worker.tasks.signal_tasks.run_all_signals",
        "args": None,
        "queue": "signals",
    }
