"""
Core Adapter — Dual-Mode Data Access Layer
==========================================

MONOREPO MODE (CORE_SERVICE_URL is empty):
  All functions delegate directly to shared.repo.queries / shared.repo.provenance.
  This is the default for local development and the current monorepo setup.

SPLIT MODE (CORE_SERVICE_URL is set):
  All functions delegate to CoreClient (HTTP calls to openwatch-core service).
  This is the target architecture after the open-core split.

POST-SPLIT CLEANUP:
  Delete the entire `if settings.CORE_SERVICE_URL:` branch and all direct shared.repo
  imports. Only the CoreClient path remains in the public repo.

Import rule:
  public.py (and any public-layer code) MUST ONLY import from this adapter.
  Never import shared.repo.* or shared.typologies.* directly from public routes.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional, Any

from sqlalchemy.ext.asyncio import AsyncSession

from shared.config import settings


# ---------------------------------------------------------------------------
# Lazy import helpers — only loaded in monorepo mode
# ---------------------------------------------------------------------------

def _queries():
    from shared.repo import queries  # noqa: PLC0415
    return queries


def _provenance():
    from shared.repo import provenance  # noqa: PLC0415
    return provenance


def _factor_metadata():
    from shared.typologies import factor_metadata  # noqa: PLC0415
    return factor_metadata


def _registry():
    from shared.typologies.registry import TypologyRegistry  # noqa: PLC0415
    return TypologyRegistry


def _baselines():
    from shared.baselines import models as bm  # noqa: PLC0415
    return bm


# ---------------------------------------------------------------------------
# Mode check
# ---------------------------------------------------------------------------

def _use_core_service() -> bool:
    return bool(settings.CORE_SERVICE_URL)


# ---------------------------------------------------------------------------
# Query adapters — one function per public use-case
# ---------------------------------------------------------------------------

async def adapter_get_coverage_v2_summary(session: AsyncSession) -> Any:
    if _use_core_service():
        from api.core_client import CoreClient
        return await CoreClient().get_coverage_summary()
    return await _queries().get_coverage_v2_summary(session)


async def adapter_get_coverage_v2_sources(session: AsyncSession, **kwargs: Any) -> Any:
    if _use_core_service():
        from api.core_client import CoreClient
        return await CoreClient().get_coverage_sources(**kwargs)
    return await _queries().get_coverage_v2_sources(session, **kwargs)


async def adapter_get_coverage_v2_source_preview(session: AsyncSession, **kwargs: Any) -> Any:
    if _use_core_service():
        from api.core_client import CoreClient
        return await CoreClient().get_coverage_source_preview(**kwargs)
    return await _queries().get_coverage_v2_source_preview(session, **kwargs)


async def adapter_get_coverage_v2_map(session: AsyncSession, **kwargs: Any) -> Any:
    if _use_core_service():
        from api.core_client import CoreClient
        return await CoreClient().get_coverage_map(**kwargs)
    return await _queries().get_coverage_v2_map(session, **kwargs)


async def adapter_get_coverage_v2_analytics(session: AsyncSession) -> Any:
    if _use_core_service():
        from api.core_client import CoreClient
        return await CoreClient().get_coverage_analytics()
    return await _queries().get_coverage_v2_analytics(session)


async def adapter_get_coverage_v2_run_detail(session: AsyncSession, run_id: uuid.UUID) -> Any:
    if _use_core_service():
        from api.core_client import CoreClient
        return await CoreClient().get_coverage_run_detail(str(run_id))
    return await _queries().get_coverage_v2_run_detail(session, run_id)


async def adapter_get_public_sources(session: AsyncSession) -> Any:
    if _use_core_service():
        from api.core_client import CoreClient
        return await CoreClient().get_public_sources()
    return await _queries().get_public_sources(session)


async def adapter_get_radar_v2_summary(session: AsyncSession, **kwargs: Any) -> Any:
    if _use_core_service():
        from api.core_client import CoreClient
        return await CoreClient().get_radar_summary(**kwargs)
    return await _queries().get_radar_v2_summary(session, **kwargs)


async def adapter_get_radar_v2_signals(session: AsyncSession, **kwargs: Any) -> Any:
    if _use_core_service():
        from api.core_client import CoreClient
        return await CoreClient().get_radar_signals(**kwargs)
    return await _queries().get_radar_v2_signals(session, **kwargs)


async def adapter_get_radar_v2_signal_preview(session: AsyncSession, signal_id: uuid.UUID) -> Any:
    if _use_core_service():
        from api.core_client import CoreClient
        return await CoreClient().get_radar_signal_preview(str(signal_id))
    return await _queries().get_radar_v2_signal_preview(session, signal_id)


async def adapter_get_radar_v2_cases(session: AsyncSession, **kwargs: Any) -> Any:
    if _use_core_service():
        from api.core_client import CoreClient
        return await CoreClient().get_radar_cases(**kwargs)
    return await _queries().get_radar_v2_cases(session, **kwargs)


async def adapter_get_radar_v2_case_preview(session: AsyncSession, case_id: uuid.UUID) -> Any:
    if _use_core_service():
        from api.core_client import CoreClient
        return await CoreClient().get_radar_case_preview(str(case_id))
    return await _queries().get_radar_v2_case_preview(session, case_id)


async def adapter_get_radar_v2_coverage(session: AsyncSession, **kwargs: Any) -> Any:
    if _use_core_service():
        from api.core_client import CoreClient
        return await CoreClient().get_radar_coverage(**kwargs)
    return await _queries().get_radar_v2_coverage(session, **kwargs)


async def adapter_search_entities(session: AsyncSession, **kwargs: Any) -> Any:
    if _use_core_service():
        from api.core_client import CoreClient
        return await CoreClient().search_entities(**kwargs)
    return await _queries().search_entities(session, **kwargs)


async def adapter_get_entity_by_id(session: AsyncSession, entity_id: uuid.UUID) -> Any:
    if _use_core_service():
        from api.core_client import CoreClient
        return await CoreClient().get_entity(str(entity_id))
    return await _queries().get_entity_by_id(session, entity_id)


async def adapter_get_org_summary(session: AsyncSession, entity_id: uuid.UUID) -> Any:
    if _use_core_service():
        from api.core_client import CoreClient
        return await CoreClient().get_org_summary(str(entity_id))
    return await _queries().get_org_summary(session, entity_id)


async def adapter_get_case_by_id(session: AsyncSession, case_id: uuid.UUID) -> Any:
    if _use_core_service():
        from api.core_client import CoreClient
        return await CoreClient().get_case(str(case_id))
    return await _queries().get_case_by_id(session, case_id)


async def adapter_get_case_entities_with_roles(session: AsyncSession, case_id: uuid.UUID) -> Any:
    if _use_core_service():
        from api.core_client import CoreClient
        return await CoreClient().get_case_entities(str(case_id))
    return await _queries().get_case_entities_with_roles(session, case_id)


async def adapter_get_case_graph(session: AsyncSession, case_id: uuid.UUID) -> Any:
    if _use_core_service():
        from api.core_client import CoreClient
        return await CoreClient().get_case_graph(str(case_id))
    return await _queries().get_case_graph(session, case_id)


async def adapter_get_signal_by_id(session: AsyncSession, signal_id: uuid.UUID) -> Any:
    if _use_core_service():
        from api.core_client import CoreClient
        return await CoreClient().get_signal(str(signal_id))
    return await _queries().get_signal_by_id(session, signal_id)


async def adapter_get_signal_detail(session: AsyncSession, signal_id: uuid.UUID) -> Any:
    if _use_core_service():
        from api.core_client import CoreClient
        return await CoreClient().get_signal_detail(str(signal_id))
    return await _queries().get_signal_detail(session, signal_id)


async def adapter_get_signal_graph(session: AsyncSession, signal_id: uuid.UUID) -> Any:
    if _use_core_service():
        from api.core_client import CoreClient
        return await CoreClient().get_signal_graph(str(signal_id))
    return await _queries().get_signal_graph(session, signal_id)


async def adapter_get_signal_evidence_page(session: AsyncSession, **kwargs: Any) -> Any:
    if _use_core_service():
        from api.core_client import CoreClient
        return await CoreClient().get_signal_evidence(**kwargs)
    return await _queries().get_signal_evidence_page(session, **kwargs)


async def adapter_replay_signal(session: AsyncSession, signal_id: uuid.UUID) -> Any:
    if _use_core_service():
        from api.core_client import CoreClient
        return await CoreClient().replay_signal(str(signal_id))
    return await _queries().replay_signal(session, signal_id)


async def adapter_get_evidence_package_by_id(session: AsyncSession, package_id: uuid.UUID) -> Any:
    if _use_core_service():
        from api.core_client import CoreClient
        return await CoreClient().get_evidence_package(str(package_id))
    return await _queries().get_evidence_package_by_id(session, package_id)


async def adapter_get_dossier_summary(session: AsyncSession, entity_id: uuid.UUID) -> Any:
    if _use_core_service():
        from api.core_client import CoreClient
        return await CoreClient().get_dossier_summary(str(entity_id))
    return await _queries().get_dossier_summary(session, entity_id)


async def adapter_get_dossier_timeline(session: AsyncSession, entity_id: uuid.UUID, **kwargs: Any) -> Any:
    if _use_core_service():
        from api.core_client import CoreClient
        return await CoreClient().get_dossier_timeline(str(entity_id), **kwargs)
    return await _queries().get_dossier_timeline(session, entity_id, **kwargs)


async def adapter_get_entity_path(session: AsyncSession, **kwargs: Any) -> Any:
    if _use_core_service():
        from api.core_client import CoreClient
        return await CoreClient().get_entity_path(**kwargs)
    return await _queries().get_entity_path(session, **kwargs)


async def adapter_get_graph_neighborhood(session: AsyncSession, **kwargs: Any) -> Any:
    if _use_core_service():
        from api.core_client import CoreClient
        return await CoreClient().get_graph_neighborhood(**kwargs)
    return await _queries().get_graph_neighborhood(session, **kwargs)


async def adapter_get_signal_provenance(session: AsyncSession, signal_id: uuid.UUID) -> Any:
    if _use_core_service():
        from api.core_client import CoreClient
        return await CoreClient().get_signal_provenance(str(signal_id))
    return await _provenance().get_raw_sources_for_event(session, signal_id)


async def adapter_get_case_provenance(session: AsyncSession, case_id: uuid.UUID) -> Any:
    if _use_core_service():
        from api.core_client import CoreClient
        return await CoreClient().get_case_provenance(str(case_id))
    return await _provenance().get_case_provenance_web(session, case_id)


async def adapter_get_baseline(session: AsyncSession, baseline_type: str, scope_key: str) -> Any:
    if _use_core_service():
        from api.core_client import CoreClient
        return await CoreClient().get_baseline(baseline_type=baseline_type, scope_key=scope_key)
    q = _queries()
    return await q.get_baseline(session, baseline_type, scope_key)


# ---------------------------------------------------------------------------
# Typology metadata — read-only reference data (safe to expose publicly)
# ---------------------------------------------------------------------------

def adapter_get_factor_descriptions(factors: dict, typology_code: Optional[str] = None) -> dict:
    """Returns human-readable factor descriptions for a signal's factors dict."""
    if _use_core_service():
        # In split mode, factor descriptions are embedded in the signal response from core.
        return {}
    return _factor_metadata().get_factor_descriptions(factors, typology_code=typology_code)


def adapter_get_typology_legal_metadata(code: str) -> Optional[dict]:
    """Returns legal metadata (laws, articles) for a typology code."""
    if _use_core_service():
        # In split mode, returned inline from core service get_typology endpoint.
        return None
    return _factor_metadata().TYPOLOGY_LEGAL_METADATA.get(code.upper())


def adapter_list_typologies() -> list[dict]:
    """Returns all registered typologies with their metadata."""
    if _use_core_service():
        # In split mode: CoreClient.list_typologies() — implement as needed.
        return []
    registry = _registry()
    fm = _factor_metadata()
    items = []
    for code, cls in registry.items():
        typology = cls()
        meta = fm.TYPOLOGY_LEGAL_METADATA.get(code, {})
        items.append({
            "code": typology.id,
            "name": typology.name,
            "corruption_types": meta.get("corruption_types", []),
            "spheres": meta.get("spheres", []),
            "evidence_level": meta.get("evidence_level", ""),
            "description_legal": meta.get("description_legal", ""),
            "law_articles": meta.get("law_articles", []),
        })
    return items


def adapter_get_typology(code: str) -> Optional[dict]:
    """Returns metadata for a single typology by code."""
    if _use_core_service():
        return None
    registry = _registry()
    fm = _factor_metadata()
    upper = code.upper()
    cls = registry.get(upper)
    if cls is None:
        return None
    typology = cls()
    meta = fm.TYPOLOGY_LEGAL_METADATA.get(upper, {})
    return {
        "code": typology.id,
        "name": typology.name,
        "corruption_types": meta.get("corruption_types", []),
        "spheres": meta.get("spheres", []),
        "evidence_level": meta.get("evidence_level", ""),
        "description_legal": meta.get("description_legal", ""),
        "law_articles": meta.get("law_articles", []),
        "factors": meta.get("factors", []),
    }
