from shared.scheduler.schedule import BEAT_SCHEDULE


class TestBeatSchedule:
    def test_has_13_entries(self):
        assert len(BEAT_SCHEDULE) == 18

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

    def test_classify_texts_entry(self):
        entry = BEAT_SCHEDULE["classify-texts-daily"]
        assert entry["task"] == "worker.tasks.ai_tasks.classify_texts_unclassified"
        assert entry["options"]["queue"] == "ai"

    def test_all_have_queue(self):
        for name, entry in BEAT_SCHEDULE.items():
            assert "options" in entry, f"{name} missing options"
            assert "queue" in entry["options"], f"{name} missing queue"

    # ── Regression: pipeline-watchdog ────────────────────────────────
    # Bug: pipeline stages ran on fixed cron times regardless of whether ingest
    # had finished, causing ER to run on partial data or typologies on stale baselines.
    # Fix: pipeline_watchdog task runs every 15 min, checks conditions, dispatches chain.

    def test_pipeline_watchdog_entry_exists(self):
        assert "pipeline-watchdog" in BEAT_SCHEDULE, (
            "pipeline-watchdog missing from beat schedule — automated pipeline will not trigger"
        )

    def test_pipeline_watchdog_task_name(self):
        entry = BEAT_SCHEDULE["pipeline-watchdog"]
        assert entry["task"] == "worker.tasks.maintenance_tasks.pipeline_watchdog"

    def test_pipeline_watchdog_uses_default_queue(self):
        entry = BEAT_SCHEDULE["pipeline-watchdog"]
        assert entry["options"]["queue"] == "default"

    def test_pipeline_watchdog_runs_frequently(self):
        """Watchdog must run often enough to react to finished ingest batches."""
        from celery.schedules import crontab
        entry = BEAT_SCHEDULE["pipeline-watchdog"]
        schedule = entry["schedule"]
        assert isinstance(schedule, crontab), "pipeline-watchdog schedule must be a crontab"
        # Verify it runs every N minutes (minute pattern like "*/15" or "*/10")
        minute = str(schedule._orig_minute)
        assert minute.startswith("*/"), (
            f"pipeline-watchdog should run every N minutes, got minute={minute!r}"
        )
