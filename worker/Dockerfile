FROM python:3.12-slim AS base

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY shared/ shared/
COPY worker/ worker/

RUN pip install --no-cache-dir -e .

ENV PYTHONPATH=/app

CMD ["celery", "-A", "worker.worker_app", "worker", "--loglevel=info"]
