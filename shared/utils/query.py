"""Database query helpers — safe chunking for large IN clauses.

asyncpg limits query parameters to 32 767.  When an ``IN (...)`` clause may
exceed that threshold we split the id-list into batches and merge results
in-memory.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TypeVar

from sqlalchemy import Select

_T = TypeVar("_T")

#: Maximum ids per ``IN (...)`` clause — well below the asyncpg 32 767 cap.
IN_CLAUSE_BATCH_SIZE: int = 5_000


async def execute_chunked_in(
    session,
    stmt_factory,
    ids: Sequence,
    *,
    batch_size: int = IN_CLAUSE_BATCH_SIZE,
) -> list:
    """Execute *stmt_factory(batch)* for each chunk and return merged scalars.

    Parameters
    ----------
    session:
        An async SQLAlchemy session (``AsyncSession``).
    stmt_factory:
        A callable ``(batch: list) -> Select`` that builds the query for one
        chunk of ids.  E.g.::

            lambda batch: select(Entity).where(Entity.id.in_(batch))

    ids:
        The full list of ids to split.
    batch_size:
        Maximum number of ids per query (default 5 000).

    Returns
    -------
    list
        Concatenated ``.scalars().all()`` results from every batch.
    """
    if not ids:
        return []

    results: list = []
    id_list = list(ids)

    for offset in range(0, len(id_list), batch_size):
        batch = id_list[offset : offset + batch_size]
        stmt = stmt_factory(batch)
        result = await session.execute(stmt)
        results.extend(result.scalars().all())

    return results
