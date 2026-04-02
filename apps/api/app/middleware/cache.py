import hashlib
import json

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from openwatch_config.settings import settings

# Headers that are safe to replay from a cached response.
# Excludes: Set-Cookie (session leakage), Content-Encoding/Transfer-Encoding
# (no longer accurate after body buffering), Content-Length (recalculated).
_SAFE_HEADERS = frozenset({
    "content-type",
    "cache-control",
    "etag",
    "last-modified",
    "vary",
    "x-request-id",
    "access-control-allow-origin",
    "access-control-allow-methods",
    "access-control-allow-headers",
})


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
                    media_type=data["media_type"],
                )
        except Exception:
            pass

        response = await call_next(request)

        # Cache successful responses
        if response.status_code == 200:
            chunks: list[bytes] = []
            async for chunk in response.body_iterator:
                chunks.append(chunk if isinstance(chunk, bytes) else chunk.encode())
            body = b"".join(chunks)

            # Capture the actual content-type so we can replay it accurately.
            original_media_type = response.headers.get("content-type", "application/json")

            # Use longer TTL for unfiltered radar summary
            ttl = settings.CACHE_TTL_SECONDS
            if "/radar/v2/summary" in request.url.path and not request.url.query:
                ttl = 300  # 5 min for unfiltered summary

            # Only persist whitelisted headers to prevent leaking auth/session headers.
            safe_headers = {
                k: v
                for k, v in response.headers.items()
                if k.lower() in _SAFE_HEADERS
            }

            try:
                cache_data = json.dumps({
                    "body": body.decode(),
                    "status": response.status_code,
                    "headers": safe_headers,
                    "media_type": original_media_type,
                })
                await redis.setex(cache_key, ttl, cache_data)
            except Exception:
                pass

            return Response(
                content=body,
                status_code=response.status_code,
                headers={**safe_headers, "X-Cache": "MISS"},
                media_type=original_media_type,
            )

        return response

    def _build_key(self, request: Request) -> str:
        # Key on path + sorted query params only — excludes scheme/host so that
        # requests through different load-balancer hostnames share the same entry.
        sorted_query = "&".join(
            f"{k}={v}"
            for k, v in sorted(request.query_params.multi_items())
        )
        raw = f"{request.url.path}?{sorted_query}" if sorted_query else request.url.path
        return f"cache:{hashlib.sha256(raw.encode()).hexdigest()}"
