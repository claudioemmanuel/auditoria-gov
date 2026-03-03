import hashlib
import json

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from shared.config import settings


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

            try:
                cache_data = json.dumps({
                    "body": body.decode(),
                    "status": response.status_code,
                    "headers": dict(response.headers),
                })
                await redis.setex(cache_key, settings.CACHE_TTL_SECONDS, cache_data)
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
        return f"cache:{hashlib.md5(url.encode()).hexdigest()}"
