FROM python:3.12-slim AS base

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

# Copy workspace files for layer caching
COPY pyproject.toml uv.lock ./
COPY packages/ packages/
COPY shared/ shared/
COPY api/ api/

# ── runtime (slim — no dev-deps, no test suite) ────────────────────────────────
FROM base AS runtime

RUN uv sync --all-packages --no-dev

ENV PYTHONPATH=/app
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

CMD ["sh", "-c", "uvicorn api.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

# ── test (includes dev-deps + test suite) ─────────────────────────────────────
FROM base AS test

COPY tests/ tests/

RUN uv sync --all-packages

ENV PYTHONPATH=/app
ENV PATH="/app/.venv/bin:$PATH"
