"""Database query helpers — resilient execution for large IN clauses.

asyncpg limits bind parameters to 32 767. Large ``IN (...)`` filters are
executed in bounded chunks with parameter-aware sizing and structured
observability.
"""

from __future__ import annotations

from collections.abc import Hashable, Sequence
from math import ceil
from typing import TypeVar

from shared.logging import log

_T = TypeVar("_T", bound=Hashable)

#: Maximum ids per ``IN (...)`` clause — well below the asyncpg 32 767 cap.
IN_CLAUSE_BATCH_SIZE: int = 5_000
MAX_ASYNCPG_BIND_PARAMS: int = 32_767
PARAMETER_HEADROOM: int = 512


def _dedupe_preserve_order(ids: Sequence[_T]) -> list[_T]:
    """Remove duplicate ids while preserving deterministic query order."""
    seen: set[_T] = set()
    deduped: list[_T] = []
    for item in ids:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped


def _effective_batch_size(batch_size: int, params_per_id: int) -> int:
    """Return batch size bounded by asyncpg parameter limits."""
    safe_param_budget = max(1, MAX_ASYNCPG_BIND_PARAMS - PARAMETER_HEADROOM)
    max_ids_by_params = max(1, safe_param_budget // params_per_id)
    return max(1, min(batch_size, max_ids_by_params))


async def execute_chunked_in(
    session,
    stmt_factory,
    ids: Sequence,
    *,
    batch_size: int = IN_CLAUSE_BATCH_SIZE,
    params_per_id: int = 1,
    operation_name: str = "generic",
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
        Requested maximum ids per query (default 5 000).
    params_per_id:
        Approximate number of bind parameters introduced per id in the query.
        Default is 1 for canonical ``IN`` queries.
    operation_name:
        Human-readable operation label for structured logs.

    Returns
    -------
    list
        Concatenated ``.scalars().all()`` results from every batch.
    """
    if batch_size <= 0:
        raise ValueError("batch_size must be > 0")
    if params_per_id <= 0:
        raise ValueError("params_per_id must be > 0")
    if not ids:
        return []

    input_count = len(ids)
    id_list = _dedupe_preserve_order(ids)
    effective_batch_size = _effective_batch_size(batch_size, params_per_id)
    chunk_count = ceil(len(id_list) / effective_batch_size)

    log.debug(
        "query.execute_chunked_in",
        operation=operation_name,
        input_count=input_count,
        unique_count=len(id_list),
        deduped=input_count != len(id_list),
        requested_batch_size=batch_size,
        effective_batch_size=effective_batch_size,
        params_per_id=params_per_id,
        chunk_count=chunk_count,
    )

    results: list = []

    for offset in range(0, len(id_list), effective_batch_size):
        batch = id_list[offset : offset + effective_batch_size]
        stmt = stmt_factory(batch)
        result = await session.execute(stmt)
        results.extend(result.scalars().all())

    return results
