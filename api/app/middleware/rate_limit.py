import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from shared.config import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Redis sliding window rate limiter by client IP."""

    async def dispatch(self, request: Request, call_next):
        # Only rate limit /public/ routes
        if not request.url.path.startswith("/public"):
            return await call_next(request)

        redis = getattr(request.app.state, "redis", None)
        if redis is None:
            return await call_next(request)

        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"
        key = f"ratelimit:public:{client_ip}"
        now_ms = int(time.time() * 1000)
        window_ms = 1000

        pipe = redis.pipeline()
        pipe.zremrangebyscore(key, 0, now_ms - window_ms)
        pipe.zcard(key)
        pipe.zadd(key, {str(now_ms): now_ms})
        pipe.expire(key, 2)

        try:
            results = await pipe.execute()
            count = results[1]
        except Exception:
            # If Redis is down, allow the request
            return await call_next(request)

        if count >= settings.PUBLIC_RATE_LIMIT_BURST:
            retry_after = 1
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests"},
                headers={"Retry-After": str(retry_after)},
            )

        return await call_next(request)
