"""Core Adapter — Public Gateway Layer.

The open-source `openwatch` repository no longer imports or executes protected
analytics, ER, typology, or repository code directly. All investigative data
access is delegated to the private `openwatch-core` service through
`api.core_client.CoreClient`.
"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.core_client import CoreClient
from shared.config import settings
from shared.models.typology_catalog import get_public_typology, list_public_typologies


def _client() -> CoreClient:
    if not settings.CORE_SERVICE_URL:
        raise RuntimeError(
            "CORE_SERVICE_URL is not configured. The public OpenWatch API must connect to openwatch-core."
        )
    if not settings.CORE_API_KEY:
        raise RuntimeError(
            "CORE_API_KEY is required when CORE_SERVICE_URL is configured."
        )
    return CoreClient()


async def adapter_get_coverage_v2_summary(session: AsyncSession) -> Any:
    _ = session
    return await _client().get_coverage_summary()


async def adapter_get_coverage_v2_sources(session: AsyncSession, **kwargs: Any) -> Any:
    _ = session
    return await _client().get_coverage_sources(**kwargs)


async def adapter_get_coverage_v2_source_preview(session: AsyncSession, **kwargs: Any) -> Any:
    _ = session
    return await _client().get_coverage_source_preview(**kwargs)


async def adapter_get_coverage_v2_map(session: AsyncSession, **kwargs: Any) -> Any:
    _ = session
    return await _client().get_coverage_map(**kwargs)


async def adapter_get_coverage_v2_analytics(session: AsyncSession) -> Any:
    _ = session
    return await _client().get_coverage_analytics()


async def adapter_get_coverage_v2_run_detail(session: AsyncSession, run_id: uuid.UUID) -> Any:
    _ = session
    return await _client().get_coverage_run_detail(str(run_id))


async def adapter_get_public_sources(session: AsyncSession) -> Any:
    _ = session
    return await _client().get_public_sources()


async def adapter_get_radar_v2_summary(session: AsyncSession, **kwargs: Any) -> Any:
    _ = session
    return await _client().get_radar_summary(**kwargs)


async def adapter_get_radar_v2_signals(session: AsyncSession, **kwargs: Any) -> Any:
    _ = session
    return await _client().get_radar_signals(**kwargs)


async def adapter_get_radar_v2_signal_preview(session: AsyncSession, signal_id: uuid.UUID) -> Any:
    _ = session
    return await _client().get_radar_signal_preview(str(signal_id))


async def adapter_get_radar_v2_cases(session: AsyncSession, **kwargs: Any) -> Any:
    _ = session
    return await _client().get_radar_cases(**kwargs)


async def adapter_get_radar_v2_case_preview(session: AsyncSession, case_id: uuid.UUID) -> Any:
    _ = session
    return await _client().get_radar_case_preview(str(case_id))


async def adapter_get_radar_v2_coverage(session: AsyncSession, **kwargs: Any) -> Any:
    _ = session
    return await _client().get_radar_coverage(**kwargs)


async def adapter_search_entities(session: AsyncSession, **kwargs: Any) -> Any:
    _ = session
    return await _client().search_entities(**kwargs)


async def adapter_get_entity_by_id(session: AsyncSession, entity_id: uuid.UUID) -> Any:
    _ = session
    return await _client().get_entity(str(entity_id))


async def adapter_get_org_summary(session: AsyncSession, entity_id: uuid.UUID) -> Any:
    _ = session
    return await _client().get_org_summary(str(entity_id))


async def adapter_get_case_by_id(session: AsyncSession, case_id: uuid.UUID) -> Any:
    _ = session
    return await _client().get_case(str(case_id))


async def adapter_get_case_entities_with_roles(session: AsyncSession, case_id: uuid.UUID) -> Any:
    _ = session
    return await _client().get_case_entities(str(case_id))


async def adapter_get_case_graph(session: AsyncSession, case_id: uuid.UUID) -> Any:
    _ = session
    return await _client().get_case_graph(str(case_id))


async def adapter_get_signal_by_id(session: AsyncSession, signal_id: uuid.UUID) -> Any:
    _ = session
    return await _client().get_signal(str(signal_id))


async def adapter_get_signal_detail(session: AsyncSession, signal_id: uuid.UUID) -> Any:
    _ = session
    return await _client().get_signal_detail(str(signal_id))


async def adapter_get_signal_graph(session: AsyncSession, signal_id: uuid.UUID) -> Any:
    _ = session
    return await _client().get_signal_graph(str(signal_id))


async def adapter_get_signal_evidence_page(session: AsyncSession, **kwargs: Any) -> Any:
    _ = session
    return await _client().get_signal_evidence(**kwargs)


async def adapter_replay_signal(session: AsyncSession, signal_id: uuid.UUID) -> Any:
    _ = session
    return await _client().replay_signal(str(signal_id))


async def adapter_get_evidence_package_by_id(session: AsyncSession, package_id: uuid.UUID) -> Any:
    _ = session
    return await _client().get_evidence_package(str(package_id))


async def adapter_get_dossier_summary(session: AsyncSession, entity_id: uuid.UUID) -> Any:
    _ = session
    return await _client().get_dossier_summary(str(entity_id))


async def adapter_get_dossier_timeline(session: AsyncSession, entity_id: uuid.UUID, **kwargs: Any) -> Any:
    _ = session
    return await _client().get_dossier_timeline(str(entity_id), **kwargs)


async def adapter_get_entity_path(session: AsyncSession, **kwargs: Any) -> Any:
    _ = session
    return await _client().get_entity_path(**kwargs)


async def adapter_get_graph_neighborhood(session: AsyncSession, **kwargs: Any) -> Any:
    _ = session
    return await _client().get_graph_neighborhood(**kwargs)


async def adapter_get_signal_provenance(session: AsyncSession, signal_id: uuid.UUID) -> Any:
    _ = session
    return await _client().get_signal_provenance(str(signal_id))


async def adapter_get_case_provenance(session: AsyncSession, case_id: uuid.UUID) -> Any:
    _ = session
    return await _client().get_case_provenance(str(case_id))


async def adapter_get_baseline(session: AsyncSession, baseline_type: str, scope_key: str) -> Any:
    _ = session
    return await _client().get_baseline(
        baseline_type=baseline_type,
        scope_key=scope_key,
    )


def adapter_get_factor_descriptions(factors: dict, typology_code: str | None = None) -> dict:
    """Return safe public descriptions for factor keys.

    When detailed factor metadata is unavailable from `openwatch-core`, the
    public layer still returns a stable key -> human label mapping so dossier and
    case-detail views remain intelligible.
    """
    _ = typology_code
    return {
        key: key.replace("_", " ").strip().capitalize()
        for key in (factors or {})
    }


def adapter_get_typology_legal_metadata(code: str) -> dict | None:
    item = get_public_typology(code)
    if item is None:
        return None
    return {
        "corruption_types": item.get("corruption_types", []),
        "spheres": item.get("spheres", []),
        "evidence_level": item.get("evidence_level", ""),
        "description_legal": item.get("description_legal", ""),
        "law_articles": item.get("law_articles", []),
    }


def adapter_list_typologies() -> list[dict]:
    return list_public_typologies()


def adapter_get_typology(code: str) -> dict | None:
    return get_public_typology(code)

