FROM python:3.12-slim AS base

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install --no-cache-dir uv

# Copy workspace config first for better layer caching
COPY pyproject.toml uv.lock ./
COPY packages/ packages/
COPY core/ core/
COPY apps/api/ apps/api/

RUN uv sync --no-dev --package openwatch-api

RUN addgroup --system openwatch && \
    adduser --system --ingroup openwatch --home /app openwatch && \
    chown -R openwatch:openwatch /app

ENV PYTHONPATH=/app
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

USER openwatch

CMD ["sh", "-c", "alembic -c apps/api/alembic.ini upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

