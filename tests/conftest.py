import os
import uuid

import pytest

# Set test env vars before any shared imports
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
os.environ.setdefault("DATABASE_URL_SYNC", "postgresql+psycopg://test:test@localhost:5432/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/14")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/13")
os.environ.setdefault("LLM_PROVIDER", "none")
os.environ.setdefault("CPF_HASH_SALT", "test-salt")
os.environ.setdefault("APP_ENV", "development")


def make_uuid() -> uuid.UUID:
    return uuid.uuid4()
