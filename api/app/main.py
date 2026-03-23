from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import Depends, FastAPI, HTTPException, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader

from shared.config import settings
from shared.db import engine
from shared.logging import setup_logging
from api.app.routers.public import router as public_router
from api.app.routers.internal import router as internal_router
from api.app.middleware.rate_limit import RateLimitMiddleware
from api.app.middleware.cache import CacheMiddleware
from api.app.middleware.security_events import SecurityEventsMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    app.state.redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    yield
    await app.state.redis.close()
    await engine.dispose()


_is_prod = settings.APP_ENV == "production"

_internal_api_key_header = APIKeyHeader(name="X-Internal-Api-Key", auto_error=False)


async def _require_internal_key(key: str = Security(_internal_api_key_header)) -> None:
    if not key or key != settings.INTERNAL_API_KEY:
        raise HTTPException(status_code=403, detail="Forbidden")

app = FastAPI(
    title="OpenWatch",
    description="API pública para auditoria cidadã de dados federais",
    version="0.1.0",
    lifespan=lifespan,
    docs_url=None if _is_prod else "/docs",
    redoc_url=None if _is_prod else "/redoc",
    openapi_url=None if _is_prod else "/openapi.json",
)

_allowed_origins = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
app.add_middleware(SecurityEventsMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(CacheMiddleware)

app.include_router(public_router, prefix="/public", tags=["public"])
app.include_router(
    internal_router,
    prefix="/internal",
    tags=["internal"],
    dependencies=[Depends(_require_internal_key)],
)


@app.get("/health")
async def health():
    return {"status": "ok"}
