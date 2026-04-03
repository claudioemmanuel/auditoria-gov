FROM python:3.12-slim AS base

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install --no-cache-dir uv

# Copy workspace config for layer caching
COPY pyproject.toml uv.lock ./
COPY packages/ packages/
COPY shared/ shared/
COPY api/ api/

RUN uv sync --no-dev --package openwatch-api 2>/dev/null || uv sync --no-dev

ENV PYTHONPATH=/app
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

CMD ["sh", "-c", "uv run alembic -c api/alembic.ini upgrade head && uv run uvicorn api.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
