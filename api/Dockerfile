FROM python:3.12-slim AS base

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

# Copy workspace files for layer caching
COPY pyproject.toml uv.lock ./
COPY packages/ packages/
COPY shared/ shared/
COPY api/ api/
COPY tests/ tests/

# Install all packages + dev deps (needed for make test inside container)
RUN uv sync --all-packages

ENV PYTHONPATH=/app
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

CMD ["sh", "-c", "alembic -c api/alembic.ini upgrade head && uvicorn api.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
