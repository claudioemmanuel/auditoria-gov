import hashlib
import json

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from openwatch_config import settings


async def cache_invalidate_pattern(redis, pattern: str) -> int:
    """Invalidate all cache keys matching a glob pattern using SCAN + DEL.

    Example: cache_invalidate_pattern(redis, "cache:*radar*")
    Returns the number of keys deleted.
    """
    if redis is None:
        return 0
    deleted = 0
    try:
        cursor = 0
        while True:
            cursor, keys = await redis.scan(cursor, match=pattern, count=200)
            if keys:
                await redis.delete(*keys)
                deleted += len(keys)
            if cursor == 0:
                break
    except Exception:
        pass
    return deleted


async def cache_invalidate_radar(redis) -> int:
    """Invalidate all radar and case-related cache entries."""
    total = 0
    for pattern in ("cache:*radar*", "cache:*case*", "cache:*signal*"):
        total += await cache_invalidate_pattern(redis, pattern)
    return total


class CacheMiddleware(BaseHTTPMiddleware):
    """Redis GET cache on /public/ routes with configurable TTL."""

    async def dispatch(self, request: Request, call_next):
        # Only cache GET requests on /public/ routes
        if request.method != "GET" or not request.url.path.startswith("/public"):
            return await call_next(request)

        redis = getattr(request.app.state, "redis", None)
        if redis is None:
            return await call_next(request)

        # Build cache key from path + query params
        cache_key = self._build_key(request)

        try:
            cached = await redis.get(cache_key)
            if cached:
                data = json.loads(cached)
                return Response(
                    content=data["body"],
                    status_code=data["status"],
                    headers={**data["headers"], "X-Cache": "HIT"},
                    media_type="application/json",
                )
        except Exception:
            pass

        response = await call_next(request)

        # Cache successful responses
        if response.status_code == 200:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk if isinstance(chunk, bytes) else chunk.encode()

            # Use longer TTL for unfiltered radar summary
            ttl = settings.CACHE_TTL_SECONDS
            if "/radar/v2/summary" in request.url.path and not request.url.query:
                ttl = 300  # 5 min for unfiltered summary

            try:
                cache_data = json.dumps({
                    "body": body.decode(),
                    "status": response.status_code,
                    "headers": dict(response.headers),
                })
                await redis.setex(cache_key, ttl, cache_data)
            except Exception:
                pass

            return Response(
                content=body,
                status_code=response.status_code,
                headers={**dict(response.headers), "X-Cache": "MISS"},
                media_type="application/json",
            )

        return response

    def _build_key(self, request: Request) -> str:
        url = str(request.url)
        return f"cache:{hashlib.sha256(url.encode()).hexdigest()}"
