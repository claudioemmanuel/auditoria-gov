from shared.scheduler.schedule import BEAT_SCHEDULE


class TestBeatSchedule:
    def test_has_8_entries(self):
        assert len(BEAT_SCHEDULE) == 8

    def test_ingest_entry(self):
        entry = BEAT_SCHEDULE["ingest-all-incremental"]
        assert entry["task"] == "worker.tasks.ingest_tasks.ingest_all_incremental"
        assert "schedule" in entry

    def test_baselines_entry(self):
        entry = BEAT_SCHEDULE["compute-baselines-daily"]
        assert entry["task"] == "worker.tasks.baseline_tasks.compute_all_baselines"

    def test_signals_entry(self):
        entry = BEAT_SCHEDULE["run-all-signals-daily"]
        assert entry["task"] == "worker.tasks.signal_tasks.run_all_signals"

    def test_coverage_entry(self):
        entry = BEAT_SCHEDULE["update-coverage-daily"]
        assert entry["task"] == "worker.tasks.coverage_tasks.update_coverage_registry"

    def test_explain_entry(self):
        entry = BEAT_SCHEDULE["explain-pending-signals"]
        assert entry["task"] == "worker.tasks.ai_tasks.explain_pending_signals"

    def test_all_have_queue(self):
        for name, entry in BEAT_SCHEDULE.items():
            assert "options" in entry, f"{name} missing options"
            assert "queue" in entry["options"], f"{name} missing queue"
