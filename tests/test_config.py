from shared.config import Settings, settings


class TestSettings:
    def test_singleton_exists(self):
        assert settings is not None

    def test_default_llm_provider(self):
        assert settings.LLM_PROVIDER in ("none", "openai")

    def test_default_rate_limits(self):
        assert settings.PUBLIC_RATE_LIMIT_RPS > 0
        assert settings.PUBLIC_RATE_LIMIT_BURST > 0

    def test_cache_ttl_positive(self):
        assert settings.CACHE_TTL_SECONDS > 0

    def test_cpf_hash_salt_set(self):
        assert len(settings.CPF_HASH_SALT) > 0

    def test_app_env(self):
        assert settings.APP_ENV in ("development", "staging", "production")

    def test_settings_extra_ignore(self):
        """Ensure extra env vars don't cause validation errors."""
        s = Settings(
            DATABASE_URL="postgresql+asyncpg://x:x@localhost/x",
            DATABASE_URL_SYNC="postgresql+psycopg://x:x@localhost/x",
            SOME_RANDOM_VAR="ignored",
        )
        assert s.DATABASE_URL == "postgresql+asyncpg://x:x@localhost/x"
