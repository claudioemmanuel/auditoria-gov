from worker.tasks import baseline_tasks


def test_compute_all_baselines_uses_async_session(monkeypatch):
    async def _fake_compute(_session):
        return ["baseline-a", "baseline-b"]

    class _FakeAsyncSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def commit(self):
            return None

    used_async_session = {"value": False}

    def _fake_async_session():
        used_async_session["value"] = True
        return _FakeAsyncSession()

    def _sync_session_must_not_be_used(*_args, **_kwargs):
        raise AssertionError(
            "compute_all_baselines must use async_session, not SyncSession"
        )

    import shared.baselines.compute as compute_module
    import shared.db as db_module
    import shared.db_sync as db_sync_module

    monkeypatch.setattr(compute_module, "compute_all_baselines", _fake_compute)
    monkeypatch.setattr(db_module, "async_session", _fake_async_session)
    monkeypatch.setattr(db_sync_module, "SyncSession", _sync_session_must_not_be_used)

    result = baseline_tasks.compute_all_baselines()

    assert used_async_session["value"] is True
    assert result == {"status": "completed", "baselines_computed": 2}
