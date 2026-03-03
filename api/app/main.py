from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shared.config import settings
from shared.db import engine
from shared.logging import setup_logging
from api.app.routers.public import router as public_router
from api.app.routers.internal import router as internal_router
from api.app.middleware.rate_limit import RateLimitMiddleware
from api.app.middleware.cache import CacheMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    app.state.redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    yield
    await app.state.redis.close()
    await engine.dispose()


app = FastAPI(
    title="AuditorIA Gov",
    description="API pública para auditoria cidadã de dados federais",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(CacheMiddleware)

app.include_router(public_router, prefix="/public", tags=["public"])
app.include_router(internal_router, prefix="/internal", tags=["internal"])


@app.get("/health")
async def health():
    return {"status": "ok"}
