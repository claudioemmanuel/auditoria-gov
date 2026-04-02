#!/usr/bin/env bash
set -e

# Support --run-pipeline mode for ECS Scheduled Tasks
if [ "$1" = "--run-pipeline" ]; then
    shift
    exec python -m worker.run_pipeline "$@"
fi

exec "$@"
