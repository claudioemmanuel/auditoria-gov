import asyncio
import time

import redis.asyncio as aioredis


class RateLimiter:
    """Redis sliding window rate limiter for outgoing API calls."""

    def __init__(self, redis_client: aioredis.Redis, key_prefix: str, rps: int):
        self.redis = redis_client
        self.key_prefix = key_prefix
        self.rps = rps
        self.window_ms = 1000

    async def acquire(self) -> None:
        """Block until a request slot is available."""
        key = f"ratelimit:{self.key_prefix}"
        while True:
            now_ms = int(time.time() * 1000)
            window_start = now_ms - self.window_ms

            pipe = self.redis.pipeline()
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zcard(key)
            pipe.zadd(key, {str(now_ms): now_ms})
            pipe.expire(key, 2)
            results = await pipe.execute()

            count = results[1]
            if count < self.rps:
                return

            await asyncio.sleep(1.0 / self.rps)
