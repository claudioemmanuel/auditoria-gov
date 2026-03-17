import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from shared.config import settings


def _client_ip(request: Request) -> str:
    """Return the real client IP.

    In the AWS ALB deployment the ALB appends the original client IP as the
    *last* entry of X-Forwarded-For, making it the only trustworthy value.
    Intermediate proxies may inject arbitrary earlier entries, so we always
    take the rightmost entry when the header is present.
    """
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        parts = [p.strip() for p in forwarded_for.split(",") if p.strip()]
        if parts:
            return parts[-1]
    return request.client.host if request.client else "unknown"


async def _check_rate_limit(redis, key: str, burst: int) -> bool:
    """Sliding-window counter. Returns True if the request should be blocked."""
    now_ms = int(time.time() * 1000)
    window_ms = 1000

    pipe = redis.pipeline()
    pipe.zremrangebyscore(key, 0, now_ms - window_ms)
    pipe.zcard(key)
    pipe.zadd(key, {str(now_ms): now_ms})
    pipe.expire(key, 2)

    try:
        results = await pipe.execute()
        return results[1] >= burst
    except Exception:
        return False  # Redis down → allow


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Redis sliding-window rate limiter.

    - /public/*   — keyed on real client IP, PUBLIC_RATE_LIMIT_BURST per second.
    - /internal/* — keyed on X-Internal-Api-Key, INTERNAL_RATE_LIMIT_BURST per second.
    - All other paths pass through unthrottled.
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        redis = getattr(request.app.state, "redis", None)

        if path.startswith("/public"):
            if redis is not None:
                ip = _client_ip(request)
                blocked = await _check_rate_limit(
                    redis,
                    f"ratelimit:public:{ip}",
                    settings.PUBLIC_RATE_LIMIT_BURST,
                )
                if blocked:
                    return JSONResponse(
                        status_code=429,
                        content={"detail": "Too many requests"},
                        headers={"Retry-After": "1"},
                    )

        elif path.startswith("/internal"):
            if redis is not None:
                api_key = request.headers.get("X-Internal-Api-Key", "anonymous")
                blocked = await _check_rate_limit(
                    redis,
                    f"ratelimit:internal:{api_key}",
                    settings.INTERNAL_RATE_LIMIT_BURST,
                )
                if blocked:
                    return JSONResponse(
                        status_code=429,
                        content={"detail": "Too many requests"},
                        headers={"Retry-After": "1"},
                    )

        return await call_next(request)
