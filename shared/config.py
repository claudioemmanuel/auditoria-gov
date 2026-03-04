import os

from pydantic_settings import BaseSettings
from typing import Literal


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://auditoria:auditoria@postgres:5432/auditoria"
    DATABASE_URL_SYNC: str = "postgresql+psycopg://auditoria:auditoria@postgres:5432/auditoria"

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"

    # Portal Transparência
    PORTAL_TRANSPARENCIA_TOKEN: str = ""

    # Data directories for bulk CSV connectors
    TSE_DATA_DIR: str = "/data/tse"
    RECEITA_CNPJ_DATA_DIR: str = "/data/receita_cnpj"

    # LLM
    LLM_PROVIDER: Literal["openai", "anthropic", "none"] = "none"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-sonnet-4-6"
    EMBEDDING_MODEL: str = "text-embedding-3-small"

    # Rate Limits (outgoing)
    RATE_LIMIT_PORTAL_TRANSPARENCIA_RPS: int = 5
    RATE_LIMIT_COMPRAS_GOV_RPS: int = 10
    RATE_LIMIT_PNCP_RPS: int = 10
    RATE_LIMIT_DEFAULT_RPS: int = 5

    # Rate Limits (incoming)
    PUBLIC_RATE_LIMIT_RPS: int = 10
    PUBLIC_RATE_LIMIT_BURST: int = 30

    # Cache
    CACHE_TTL_SECONDS: int = 300

    # Celery
    CELERY_BROKER_URL: str = "redis://redis:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/2"

    # LGPD
    CPF_HASH_SALT: str = "change-me-in-production"

    # App
    APP_ENV: Literal["development", "staging", "production"] = "development"
    LOG_LEVEL: str = "INFO"

    # Entity Resolution thresholds
    ORG_MATCH_THRESHOLD: float = float(os.getenv("ORG_MATCH_THRESHOLD", "0.85"))
    PERSON_MATCH_THRESHOLD: float = float(os.getenv("PERSON_MATCH_THRESHOLD", "0.90"))

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
