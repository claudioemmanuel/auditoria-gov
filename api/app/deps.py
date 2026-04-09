from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from api.app.db import get_session


@dataclass
class PaginationParams:
    offset: int = 0
    limit: int = 20


def get_pagination(
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginationParams:
    return PaginationParams(offset=offset, limit=limit)


async def get_redis(request: Request):
    return request.app.state.redis


DbSession = Annotated[AsyncSession, Depends(get_session)]
Pagination = Annotated[PaginationParams, Depends(get_pagination)]
