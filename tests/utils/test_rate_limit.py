from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shared.utils.rate_limit import RateLimiter


def _make_pipe(execute_return):
    """Mock pipeline: sync chainable methods, async execute."""
    pipe = MagicMock()
    pipe.zremrangebyscore.return_value = pipe
    pipe.zcard.return_value = pipe
    pipe.zadd.return_value = pipe
    pipe.expire.return_value = pipe
    pipe.execute = AsyncMock(return_value=execute_return)
    return pipe


class TestRateLimiter:
    def test_init(self):
        redis = MagicMock()
        limiter = RateLimiter(redis, "test", 5)
        assert limiter.key_prefix == "test"
        assert limiter.rps == 5
        assert limiter.window_ms == 1000

    @pytest.mark.asyncio
    async def test_acquire_under_limit(self):
        pipe = _make_pipe([None, 2, None, None])
        redis = MagicMock()
        redis.pipeline.return_value = pipe

        limiter = RateLimiter(redis, "test", 5)
        await limiter.acquire()

        pipe.zremrangebyscore.assert_called_once()
        pipe.zcard.assert_called_once()
        pipe.zadd.assert_called_once()
        pipe.expire.assert_called_once()
        pipe.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_acquire_at_limit_waits_then_succeeds(self):
        pipe1 = _make_pipe([None, 5, None, None])
        pipe2 = _make_pipe([None, 2, None, None])

        redis = MagicMock()
        redis.pipeline.side_effect = [pipe1, pipe2]

        limiter = RateLimiter(redis, "test", 5)
        with patch("shared.utils.rate_limit.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await limiter.acquire()
            mock_sleep.assert_called_once_with(0.2)
