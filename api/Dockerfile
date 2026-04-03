FROM python:3.12-slim AS base

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY shared/ shared/
COPY api/ api/

RUN pip install --no-cache-dir -e .

ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["sh", "-c", "alembic -c api/alembic.ini upgrade head && uvicorn api.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
