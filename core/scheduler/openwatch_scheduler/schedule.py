from celery.schedules import crontab

BEAT_SCHEDULE = {
    "ingest-all-incremental": {
        "task": "openwatch_pipelines.ingest_tasks.ingest_all_incremental",
        "schedule": crontab(minute=0, hour="*/6"),  # Every 6 hours (free tier)
        "options": {"queue": "ingest"},
    },
    "ingest-all-bulk": {
        "task": "openwatch_pipelines.ingest_tasks.ingest_all_bulk",
        "schedule": crontab(minute=0, hour=0),  # Daily at midnight UTC
        "options": {"queue": "bulk"},
    },
    "run-entity-resolution": {
        "task": "openwatch_pipelines.er_tasks.run_entity_resolution",
        "schedule": crontab(minute=30, hour=1),  # Daily at 01:30
        "options": {"queue": "er"},
    },
    "compute-baselines-daily": {
        "task": "openwatch_pipelines.baseline_tasks.compute_all_baselines",
        "schedule": crontab(minute=0, hour=2),  # Daily at 02:00
        "options": {"queue": "default"},
    },
    "run-all-signals-daily": {
        "task": "openwatch_pipelines.signal_tasks.run_all_signals",
        "schedule": crontab(minute=0, hour=3),  # Daily at 03:00
        "options": {"queue": "signals"},
    },
    "build-cases-daily": {
        "task": "openwatch_pipelines.case_tasks.build_cases",
        "schedule": crontab(minute=30, hour=3),  # Daily at 03:30 — after signals
        "options": {"queue": "default"},
    },
    "update-coverage-daily": {
        "task": "openwatch_pipelines.coverage_tasks.update_coverage_registry",
        "schedule": crontab(minute=0, hour=4),  # Daily at 04:00
        "options": {"queue": "default"},
    },
    "explain-pending-signals": {
        "task": "openwatch_pipelines.ai_tasks.explain_pending_signals",
        "schedule": crontab(minute=30, hour=4),  # Daily at 04:30
        "options": {"queue": "ai"},
    },
    "classify-texts-daily": {
        "task": "openwatch_pipelines.ai_tasks.classify_texts_unclassified",
        "schedule": crontab(minute=45, hour=4),  # Daily at 04:45 UTC
        "options": {"queue": "ai"},
    },
    "pipeline-watchdog": {
        "task": "openwatch_pipelines.maintenance_tasks.pipeline_watchdog",
        "schedule": crontab(minute="*/5"),  # Every 5 minutes — ER is incremental & advisory-locked
        "options": {"queue": "default"},
    },
    "cleanup-stale-runs": {
        "task": "openwatch_pipelines.maintenance_tasks.cleanup_stale_runs",
        "schedule": crontab(minute=0, hour=5),  # Daily at 05:00
        "options": {"queue": "default"},
    },
    "purge-old-results": {
        "task": "openwatch_pipelines.maintenance_tasks.purge_old_results",
        "schedule": crontab(minute=30, hour=5),  # Daily at 05:30
        "options": {"queue": "default"},
    },
    "purge-normalized-raw-source": {
        "task": "openwatch_pipelines.maintenance_tasks.purge_normalized_raw_source",
        "schedule": crontab(minute=15, hour="*/6"),  # Every 6 hours (dev-friendly)
        "options": {"queue": "vacuum"},
    },
    "vacuum-raw-source": {
        "task": "openwatch_pipelines.maintenance_tasks.vacuum_raw_source",
        "schedule": crontab(minute=45, hour=5),  # Daily at 05:45 UTC (after purge)
        "options": {"queue": "vacuum"},
    },
    "disk-space-watchdog": {
        "task": "openwatch_pipelines.maintenance_tasks.disk_space_watchdog",
        "schedule": crontab(minute=0, hour="*/4"),  # Every 4 hours (dev-friendly)
        "options": {"queue": "default"},
    },
    "check-source-compliance-weekly": {
        "task": "openwatch_pipelines.compliance_tasks.check_source_compliance",
        "schedule": crontab(minute=0, hour=6, day_of_week=1),  # Monday 06:00 UTC
        "options": {"queue": "default"},
    },
    "normalize-drain-check": {
        "task": "openwatch_pipelines.maintenance_tasks.trigger_normalize_drain",
        "schedule": crontab(minute=0, hour="*/3"),  # Every 3 hours (dev-friendly)
        "options": {"queue": "vacuum"},
    },
    "docker-build-prune-weekly": {
        "task": "openwatch_pipelines.maintenance_tasks.docker_build_prune",
        "schedule": crontab(minute=30, hour=6, day_of_week=0),  # Sunday 06:30 UTC
        "options": {"queue": "vacuum"},
    },
}
