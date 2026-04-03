FROM python:3.12-slim AS base

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY shared/ shared/
COPY worker/ worker/

RUN pip install --no-cache-dir -e .
RUN addgroup --system openwatch && adduser --system --ingroup openwatch --home /app openwatch && chown -R openwatch:openwatch /app

ENV PYTHONPATH=/app

COPY worker/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh
USER openwatch
ENTRYPOINT ["/docker-entrypoint.sh"]

CMD ["celery", "-A", "worker.worker_app", "worker", "--loglevel=info"]
