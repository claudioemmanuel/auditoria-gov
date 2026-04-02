import os

from pydantic import model_validator
from pydantic_settings import BaseSettings
from typing import Literal


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://auditoria:auditoria@postgres:5432/auditoria"
    DATABASE_URL_SYNC: str = "postgresql+psycopg://auditoria:auditoria@postgres:5432/auditoria"

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"
    REDIS_PASSWORD: str = ""

    # Portal Transparência
    PORTAL_TRANSPARENCIA_TOKEN: str = ""

    # DataJud/CNJ — public key published by CNJ on their Wiki (Portaria Nº 160/2020)
    # See: https://datajud-wiki.cnj.jus.br/api-publica/acesso
    DATAJUD_API_KEY: str = "cDZHYzlZa0JadVREZDJCendQbXY6SkJlTzNjLV9TRENyQk1RdnFKZGRQdw=="

    # Data directories for bulk CSV connectors
    TSE_DATA_DIR: str = "/data/tse"
    RECEITA_CNPJ_DATA_DIR: str = "/data/receita_cnpj"
    ORCAMENTO_BIM_DATA_FILE: str = "/data/orcamento_bim/items.jsonl"

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
    INTERNAL_RATE_LIMIT_BURST: int = 10  # per second, keyed on API key

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
    LOG_FORMAT: Literal["json", "console"] = "json"
    SQL_ECHO: bool = False
    TYPOLOGY_WINDOW_MIN_DAYS: int = 365
    TYPOLOGY_WINDOW_MAX_DAYS: int = 3650

    # CORS — comma-separated list of allowed origins
    ALLOWED_ORIGINS: str = "http://localhost:3000"

    # Internal API authentication — set a strong secret in production
    INTERNAL_API_KEY: str = "dev-internal-key-change-in-production"

    # Entity Resolution thresholds
    ORG_MATCH_THRESHOLD: float = float(os.getenv("ORG_MATCH_THRESHOLD", "0.85"))
    PERSON_MATCH_THRESHOLD: float = float(os.getenv("PERSON_MATCH_THRESHOLD", "0.90"))

    model_config = {"env_file": ".env", "extra": "ignore"}

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        if self.APP_ENV == "production":
            if self.CPF_HASH_SALT == "change-me-in-production":
                raise ValueError(
                    "CPF_HASH_SALT must be changed before running in production (LGPD compliance)"
                )
            if self.INTERNAL_API_KEY == "dev-internal-key-change-in-production":
                raise ValueError(
                    "INTERNAL_API_KEY must be changed before running in production"
                )
            if "auditoria:auditoria@" in self.DATABASE_URL:
                raise ValueError(
                    "Default database credentials must not be used in production"
                )
        return self


settings = Settings()
