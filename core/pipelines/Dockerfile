FROM python:3.12-slim AS base

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install --no-cache-dir uv

# Copy workspace config for layer caching
COPY pyproject.toml uv.lock ./
COPY packages/ packages/
COPY core/ core/

RUN uv sync --no-dev --package openwatch-pipelines

RUN addgroup --system openwatch && \
    adduser --system --ingroup openwatch --home /app openwatch && \
    chown -R openwatch:openwatch /app

ENV PYTHONPATH=/app
ENV PATH="/app/.venv/bin:$PATH"

COPY core/pipelines/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

USER openwatch
ENTRYPOINT ["/docker-entrypoint.sh"]

CMD ["celery", "-A", "openwatch_pipelines.worker_app", "worker", "--loglevel=info"]
