from celery.schedules import crontab

BEAT_SCHEDULE = {
    "ingest-all-incremental": {
        "task": "worker.tasks.ingest_tasks.ingest_all_incremental",
        "schedule": crontab(minute=0, hour="*/2"),  # Every 2 hours
        "options": {"queue": "ingest"},
    },
    "run-entity-resolution": {
        "task": "worker.tasks.er_tasks.run_entity_resolution",
        "schedule": crontab(minute=30, hour=1),  # Daily at 01:30
        "options": {"queue": "er"},
    },
    "compute-baselines-daily": {
        "task": "worker.tasks.baseline_tasks.compute_all_baselines",
        "schedule": crontab(minute=0, hour=2),  # Daily at 02:00
        "options": {"queue": "default"},
    },
    "run-all-signals-daily": {
        "task": "worker.tasks.signal_tasks.run_all_signals",
        "schedule": crontab(minute=0, hour=3),  # Daily at 03:00
        "options": {"queue": "signals"},
    },
    "update-coverage-daily": {
        "task": "worker.tasks.coverage_tasks.update_coverage_registry",
        "schedule": crontab(minute=0, hour=4),  # Daily at 04:00
        "options": {"queue": "default"},
    },
    "explain-pending-signals": {
        "task": "worker.tasks.ai_tasks.explain_pending_signals",
        "schedule": crontab(minute=30, hour=4),  # Daily at 04:30
        "options": {"queue": "ai"},
    },
    "cleanup-stale-runs": {
        "task": "worker.tasks.maintenance_tasks.cleanup_stale_runs",
        "schedule": crontab(minute=0, hour=5),  # Daily at 05:00
        "options": {"queue": "default"},
    },
    "purge-old-results": {
        "task": "worker.tasks.maintenance_tasks.purge_old_results",
        "schedule": crontab(minute=30, hour=5),  # Daily at 05:30
        "options": {"queue": "default"},
    },
}
