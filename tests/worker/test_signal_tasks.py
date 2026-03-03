from shared.typologies.registry import get_all_typologies, get_typology
from worker.tasks import signal_tasks


def test_t08_typology_loads_from_registry():
    """Unit: typology module must be importable and registry-resolvable."""
    typology = get_typology("T08")
    assert typology.id == "T08"
    assert typology.name


def test_run_all_signals_dispatches_every_loaded_typology(monkeypatch):
    """Feature: run_all_signals must enqueue one task per loaded typology."""
    dispatched: list[str] = []

    def _fake_delay(typology_code: str, dry_run: bool = False) -> None:
        dispatched.append(typology_code)

    monkeypatch.setattr(signal_tasks.run_single_signal, "delay", _fake_delay)

    result = signal_tasks.run_all_signals()

    expected_typologies = [t.id for t in get_all_typologies()]
    assert result["status"] == "dispatched"
    assert result["count"] == len(expected_typologies)
    assert dispatched == expected_typologies


def test_run_single_signal_uses_async_session(monkeypatch):
    class _FakeTypology:
        id = "T01"
        name = "Fake T01"
        required_domains: list[str] = []

        async def run(self, session):
            _ = session
            return []

    class _FakeResult:
        def __init__(self, typology_id: str) -> None:
            self._typology_id = typology_id

        def scalar_one_or_none(self):
            return type("TypRow", (), {"id": self._typology_id})()

    class _FakeAsyncSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def execute(self, _stmt):
            return _FakeResult("typology-row-1")

        def add(self, _obj):
            return None

        async def flush(self):
            return None

        async def commit(self):
            return None

    used_async_session = {"value": False}

    def _fake_async_session():
        used_async_session["value"] = True
        return _FakeAsyncSession()

    def _sync_session_must_not_be_used(*_args, **_kwargs):
        raise AssertionError("run_single_signal must use async_session, not SyncSession")

    import shared.db as db_module
    import shared.db_sync as db_sync_module
    import shared.typologies.registry as registry_module

    monkeypatch.setattr(db_module, "async_session", _fake_async_session)
    monkeypatch.setattr(db_sync_module, "SyncSession", _sync_session_must_not_be_used)
    monkeypatch.setattr(registry_module, "get_typology", lambda _code: _FakeTypology())

    result = signal_tasks.run_single_signal("T01")
    assert used_async_session["value"] is True
    assert result == {
        "typology": "T01",
        "dry_run": False,
        "candidates": 0,
        "signals_created": 0,
        "signals_deduped": 0,
        "signals_blocked": 0,
    }


def test_compute_completeness_sufficient_signal():
    class _Ref:
        def __init__(self):
            self.url = "https://example.com"
            self.ref_id = "raw-1"
            self.source_hash = "abc"
            self.snapshot_uri = "raw://x"

    class _Signal:
        entity_ids = ["e1"]
        event_ids = ["ev1"]
        period_start = "2025-01-01"
        period_end = "2025-01-31"
        factors = {"x": 1}
        evidence_refs = [_Ref()]

    score, status = signal_tasks._compute_completeness(_Signal())
    assert score >= 0.65
    assert status == "sufficient"


def test_compute_completeness_insufficient_signal():
    class _Signal:
        entity_ids = []
        event_ids = []
        period_start = None
        period_end = None
        factors = {}
        evidence_refs = []

    score, status = signal_tasks._compute_completeness(_Signal())
    assert score < 0.65
    assert status == "insufficient"
