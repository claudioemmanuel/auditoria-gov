from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from openwatch_config.settings import settings

sync_engine = create_engine(
    settings.DATABASE_URL_SYNC,
    # SQL echo is explicit and disabled by default to avoid noisy, high-volume logs.
    echo=settings.SQL_ECHO,
    pool_size=15,
    max_overflow=25,
    # Validate connections before checkout to handle Postgres restarts gracefully.
    pool_pre_ping=True,
    # Recycle connections after 30 minutes to avoid stale-connection issues
    # behind PgBouncer or after Postgres config reload.
    pool_recycle=1800,
)

SyncSession = sessionmaker(sync_engine, class_=Session, expire_on_commit=False)
