FROM python:3.12-slim AS base

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl ntpsec-ntpdate && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY shared/ shared/
COPY worker/ worker/

RUN pip install --no-cache-dir -e .

ENV PYTHONPATH=/app

COPY worker/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh
ENTRYPOINT ["/docker-entrypoint.sh"]

CMD ["celery", "-A", "worker.worker_app", "worker", "--loglevel=info"]
