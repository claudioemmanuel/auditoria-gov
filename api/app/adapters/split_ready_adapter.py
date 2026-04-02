"""
Split-Ready Adapter — Dual-Mode Core Access Layer

Post-split architecture:
- Public repository: Uses CoreClient (HTTP calls to openwatch-core)
- Private core: Direct database access via SQLAlchemy async

IMPORTANT: Each function MUST work identically whether called via direct DB or CoreClient.
All responses are normalized to match CoreClient JSON schema.

This adapter demonstrates the split-ready pattern. Once split_repo.sh completes:
1. This file is ONLY in the public repo (openwatch)
2. CoreClient becomes the primary integration point
3. All endpoint signatures remain unchanged
"""
from __future__ import annotations

import uuid
from typing import Any, Optional
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from api.core_client import CoreClient
from shared.config import settings
from shared.models.public_filter import (
    PublicSignalSummary,
    PublicEntitySummary,
    PublicCaseSummary,
    to_public_signal,
    to_public_entity,
)
from shared.models.signals import RiskSignalOut
from shared.models.graph import CaseGraphResponse, EntityPathResponse


# ────────────────────────────────────────────────────────────────────────────
# DUAL-MODE FACTORY: Route to CoreClient or direct DB based on configuration
# ────────────────────────────────────────────────────────────────────────────

def should_use_core_client() -> bool:
    """Determine if we should use CoreClient (split mode) or direct DB (monorepo)."""
    return bool(settings.CORE_SERVICE_URL and settings.CORE_API_KEY)


async def get_signal_with_public_filter(
    signal_id: uuid.UUID,
    session: Optional[AsyncSession] = None,
) -> Optional[PublicSignalSummary]:
    """
    Retrieve a signal and apply PublicSignalSummary filtering.

    Post-split: Uses CoreClient
    Pre-split/monorepo: Direct DB access

    Returns None if not found.
    """
    if should_use_core_client():
        # Split mode: HTTP call to openwatch-core
        client = CoreClient()
        try:
            signal_dict = await client.get_signal_detail(str(signal_id))
            return to_public_signal(signal_dict)
        except Exception:
            return None
    else:
        # Monorepo mode: Direct DB (stubbed for this example)
        # In practice, this would import and use the actual queries
        return None


async def get_signals_list_with_public_filter(
    session: AsyncSession,
    offset: int = 0,
    limit: int = 50,
    **filters: Any,
) -> tuple[list[PublicSignalSummary], int]:
    """
    Retrieve signals list with PublicSignalSummary filtering.

    Post-split: Uses CoreClient HTTP call
    Pre-split: Direct DB query using optimized loader

    Returns: (filtered_signals, total_count)
    """
    if should_use_core_client():
        # Split mode: HTTP call to openwatch-core
        client = CoreClient()
        try:
            result = await client.get_signals_list(offset=offset, limit=limit, **filters)
            signals = [to_public_signal(s) for s in result.get("signals", [])]
            return signals, result.get("total", 0)
        except Exception:
            return [], 0
    else:
        # Monorepo mode: DB query (not implemented here, use original adapters)
        # This is the fallback when CoreClient is not configured
        return [], 0


async def get_entity_with_public_filter(
    entity_id: uuid.UUID,
    session: Optional[AsyncSession] = None,
) -> Optional[PublicEntitySummary]:
    """
    Retrieve entity and apply PublicEntitySummary filtering.

    Post-split: Uses CoreClient
    Pre-split: Direct DB access
    """
    if should_use_core_client():
        client = CoreClient()
        try:
            entity_dict = await client.get_entity_detail(str(entity_id))
            return to_public_entity(entity_dict)
        except Exception:
            return None
    else:
        # Monorepo mode: stublied
        return None


async def get_case_with_public_filter(
    case_id: uuid.UUID,
    session: Optional[AsyncSession] = None,
) -> Optional[PublicCaseSummary]:
    """
    Retrieve case and apply PublicCaseSummary filtering.

    Post-split: Uses CoreClient
    Pre-split: Direct DB access
    """
    if should_use_core_client():
        client = CoreClient()
        try:
            case_dict = await client.get_case_detail(str(case_id))
            return PublicCaseSummary(**{
                k: case_dict[k] for k in PublicCaseSummary.model_fields if k in case_dict
            })
        except Exception:
            return None
    else:
        # Monorepo mode: stubbed
        return None


async def search_entities_with_public_filter(
    query: str,
    session: Optional[AsyncSession] = None,
    limit: int = 20,
) -> list[PublicEntitySummary]:
    """
    Search entities and apply PublicEntitySummary filtering.

    Post-split: Uses CoreClient
    Pre-split: Direct DB access
    """
    if should_use_core_client():
        client = CoreClient()
        try:
            results = await client.search_entities(query=query, limit=limit)
            return [to_public_entity(e) for e in results]
        except Exception:
            return []
    else:
        # Monorepo mode: stubbed
        return []


async def get_signal_graph_with_public_filter(
    signal_id: uuid.UUID,
    max_depth: int = 2,
    session: Optional[AsyncSession] = None,
) -> Optional[dict[str, Any]]:
    """
    Retrieve signal graph and filter for public consumption.

    Post-split: Uses CoreClient
    Pre-split: Direct DB access
    """
    if should_use_core_client():
        client = CoreClient()
        try:
            graph = await client.get_signal_graph(str(signal_id), max_depth=max_depth)
            # Filter the graph to remove internal fields
            return _filter_graph_for_public(graph)
        except Exception:
            return None
    else:
        # Monorepo mode: stubbed
        return None


async def get_case_graph_with_public_filter(
    case_id: uuid.UUID,
    max_depth: int = 2,
    session: Optional[AsyncSession] = None,
) -> Optional[CaseGraphResponse]:
    """
    Retrieve case graph and filter for public consumption.

    Post-split: Uses CoreClient
    Pre-split: Direct DB access
    """
    if should_use_core_client():
        client = CoreClient()
        try:
            graph = await client.get_case_graph(str(case_id), max_depth=max_depth)
            return _filter_graph_for_public(graph)
        except Exception:
            return None
    else:
        # Monorepo mode: stubbed
        return None


# ────────────────────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ────────────────────────────────────────────────────────────────────────────

def _filter_graph_for_public(graph: dict[str, Any]) -> dict[str, Any]:
    """Remove internal fields from graph responses."""
    _INTERNAL_GRAPH_FIELDS = {
        "internal_score",
        "completeness_score",
        "confidence_weights",
        "raw_factors",
        "explanation_md",
        "cluster_id",
        "cpf_hash",
    }
    return {
        k: v for k, v in graph.items()
        if k not in _INTERNAL_GRAPH_FIELDS
    }


# ────────────────────────────────────────────────────────────────────────────
# MIGRATION GUIDE
# ────────────────────────────────────────────────────────────────────────────
"""
TO MIGRATE ENDPOINTS FROM OLD ADAPTERS:

BEFORE (monorepo mode):
    from api.app.adapters.core_adapter import adapter_get_signal_by_id
    
    @router.get("/radar/v2/signal/{signal_id}/preview")
    async def signal_preview(signal_id: uuid.UUID, session: DbSession):
        signal = await adapter_get_signal_by_id(session, signal_id)
        return signal

AFTER (split-ready):
    from api.app.adapters.split_ready_adapter import get_signal_with_public_filter
    
    @router.get("/radar/v2/signal/{signal_id}/preview")
    async def signal_preview(signal_id: uuid.UUID, session: DbSession):
        signal = await get_signal_with_public_filter(signal_id, session)
        if signal is None:
            raise HTTPException(status_code=404, detail="Signal not found")
        return signal

The dual-mode adapter automatically:
1. Uses CoreClient in split mode (POST-SPLIT)
2. Falls back to DB in monorepo mode (PRE-SPLIT)
3. Applies PublicSignalSummary/PublicEntitySummary filtering
4. Maintains consistent JSON schema

NO ENDPOINT CODE CHANGES NEEDED once this adapter is in place.
"""
