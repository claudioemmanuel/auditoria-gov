from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from shared.config import settings

sync_engine = create_engine(
    settings.DATABASE_URL_SYNC,
    # Only echo SQL in development — production logging has severe overhead.
    echo=(settings.APP_ENV == "development"),
    pool_size=5,
    max_overflow=10,
    # Validate connections before checkout to handle Postgres restarts gracefully.
    pool_pre_ping=True,
    # Recycle connections after 30 minutes to avoid stale-connection issues
    # behind PgBouncer or after Postgres config reload.
    pool_recycle=1800,
)

SyncSession = sessionmaker(sync_engine, class_=Session, expire_on_commit=False)
