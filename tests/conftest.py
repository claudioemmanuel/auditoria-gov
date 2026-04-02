import os
import uuid
from collections.abc import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from shared.models import Base

# Set test env vars before any shared imports
# Note: CI may inject DATABASE_URL; local Docker defaults to localhost:5432/auditoria.
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://auditoria:auditoria@localhost:5432/auditoria",
)
os.environ.setdefault(
    "DATABASE_URL_SYNC",
    "postgresql+psycopg://auditoria:auditoria@localhost:5432/auditoria",
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/14")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/13")
os.environ.setdefault("LLM_PROVIDER", "none")
os.environ.setdefault("CPF_HASH_SALT", "test-salt")
os.environ.setdefault("APP_ENV", "development")

_TEST_DB_URL = os.environ["DATABASE_URL"]  # Use env var (CI injects correct port)


@pytest.fixture
async def async_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(_TEST_DB_URL, echo=False)
    
    # Create all tables before the test
    async with engine.begin() as conn:
        # Enable pgvector extension for vector type support
        await conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS vector")
        await conn.run_sync(Base.metadata.create_all)
    
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        async with session.begin():
            yield session
            await session.rollback()
    
    # Cleanup: drop all tables after the test
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


def make_uuid() -> uuid.UUID:
    return uuid.uuid4()
