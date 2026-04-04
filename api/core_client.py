"""
Core Service Gateway Client
============================

HTTP client for the openwatch-core private service. Used by the dual-mode
core_adapter.py when CORE_SERVICE_URL is set (split mode).

Configuration:
    CORE_SERVICE_URL — internal URL of the openwatch-core API service
    CORE_API_KEY     — service-to-service authentication token

IMPORTANT: This file is intentionally a stub in the monorepo.
           It becomes the primary integration point in the public repo post-split.
"""
from __future__ import annotations

from typing import Any

import httpx

from shared.config import settings


class CoreServiceError(Exception):
    """Raised when the core service returns an error response."""


class CoreNotFoundError(CoreServiceError):
    """Raised when the core service returns a 404 Not Found response."""


class CoreClient:
    """
    Async HTTP client for the openwatch-core internal service.

    Methods map 1:1 to the internal API endpoints in openwatch-core.
    All method signatures align with the calls made in core_adapter.py.
    """

    def __init__(self) -> None:
        self._base_url = settings.CORE_SERVICE_URL.rstrip("/")
        self._api_key = settings.CORE_API_KEY
        self._timeout = httpx.Timeout(30.0, connect=5.0)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "X-Service": "openwatch-public",
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get(self, path: str, **params: Any) -> Any:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            r = await client.get(
                f"{self._base_url}{path}",
                headers=self._headers(),
                params={k: v for k, v in params.items() if v is not None},
            )
            _raise_for_status(r)
            return r.json()

    async def _post(self, path: str, body: Any = None) -> Any:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            r = await client.post(
                f"{self._base_url}{path}",
                headers=self._headers(),
                json=body,
            )
            _raise_for_status(r)
            return r.json()

    # ------------------------------------------------------------------
    # Coverage
    # ------------------------------------------------------------------

    async def get_coverage_summary(self) -> Any:
        return await self._get("/internal/coverage/summary")

    async def get_coverage_sources(self, **kwargs: Any) -> Any:
        return await self._get("/internal/coverage/sources", **kwargs)

    async def get_coverage_source_preview(self, **kwargs: Any) -> Any:
        return await self._get("/internal/coverage/source-preview", **kwargs)

    async def get_coverage_map(self, **kwargs: Any) -> Any:
        return await self._get("/internal/coverage/map", **kwargs)

    async def get_coverage_analytics(self) -> Any:
        return await self._get("/internal/coverage/analytics")

    async def get_coverage_run_detail(self, run_id: str) -> Any:
        return await self._get(f"/internal/coverage/run/{run_id}")

    async def get_public_sources(self) -> Any:
        return await self._get("/internal/coverage/public-sources")

    # ------------------------------------------------------------------
    # Radar
    # ------------------------------------------------------------------

    async def get_radar_summary(self, **kwargs: Any) -> Any:
        return await self._get("/internal/radar/summary", **kwargs)

    async def get_radar_signals(self, **kwargs: Any) -> Any:
        return await self._get("/internal/radar/signals", **kwargs)

    async def get_radar_signal_preview(self, signal_id: str) -> Any:
        return await self._get(f"/internal/radar/signal/{signal_id}/preview")

    async def get_radar_cases(self, **kwargs: Any) -> Any:
        return await self._get("/internal/radar/cases", **kwargs)

    async def get_radar_case_preview(self, case_id: str) -> Any:
        return await self._get(f"/internal/radar/case/{case_id}/preview")

    async def get_radar_coverage(self, **kwargs: Any) -> Any:
        return await self._get("/internal/radar/coverage", **kwargs)

    # ------------------------------------------------------------------
    # Entities
    # ------------------------------------------------------------------

    async def search_entities(self, **kwargs: Any) -> Any:
        return await self._get("/internal/entity/search", **kwargs)

    async def get_entity(self, entity_id: str) -> Any:
        return await self._get(f"/internal/entity/{entity_id}")

    async def get_org_summary(self, entity_id: str) -> Any:
        return await self._get(f"/internal/entity/{entity_id}/org-summary")

    async def get_dossier_summary(self, entity_id: str) -> Any:
        return await self._get(f"/internal/entity/{entity_id}/dossier/summary")

    async def get_dossier_timeline(self, entity_id: str, **kwargs: Any) -> Any:
        return await self._get(f"/internal/entity/{entity_id}/dossier/timeline", **kwargs)

    # ------------------------------------------------------------------
    # Cases
    # ------------------------------------------------------------------

    async def get_case(self, case_id: str) -> Any:
        return await self._get(f"/internal/case/{case_id}")

    async def get_case_entities(self, case_id: str) -> Any:
        return await self._get(f"/internal/case/{case_id}/entities")

    async def get_case_graph(self, case_id: str) -> Any:
        return await self._get(f"/internal/case/{case_id}/graph")

    async def get_case_provenance(self, case_id: str) -> Any:
        return await self._get(f"/internal/case/{case_id}/provenance")

    # ------------------------------------------------------------------
    # Signals
    # ------------------------------------------------------------------

    async def get_signal(self, signal_id: str) -> Any:
        return await self._get(f"/internal/signal/{signal_id}")

    async def get_signal_detail(self, signal_id: str) -> Any:
        return await self._get(f"/internal/signal/{signal_id}/detail")

    async def get_signal_graph(self, signal_id: str) -> Any:
        return await self._get(f"/internal/signal/{signal_id}/graph")

    async def get_signal_evidence(self, **kwargs: Any) -> Any:
        return await self._get("/internal/signal/evidence", **kwargs)

    async def replay_signal(self, signal_id: str) -> Any:
        return await self._post(f"/internal/signal/{signal_id}/replay")

    async def get_signal_provenance(self, signal_id: str) -> Any:
        return await self._get(f"/internal/signal/{signal_id}/provenance")

    # ------------------------------------------------------------------
    # Evidence packages
    # ------------------------------------------------------------------

    async def get_evidence_package(self, package_id: str) -> Any:
        return await self._get(f"/internal/evidence/{package_id}")

    # ------------------------------------------------------------------
    # Graph
    # ------------------------------------------------------------------

    async def get_entity_path(self, **kwargs: Any) -> Any:
        return await self._get("/internal/graph/path", **kwargs)

    async def get_graph_neighborhood(self, **kwargs: Any) -> Any:
        return await self._get("/internal/graph/neighborhood", **kwargs)

    # ------------------------------------------------------------------
    # Baselines
    # ------------------------------------------------------------------

    async def get_baseline(self, baseline_type: str, scope_key: str) -> Any:
        return await self._get(
            "/internal/baseline",
            baseline_type=baseline_type,
            scope_key=scope_key,
        )

    async def get_case_legal_hypothesis(self, case_id: str) -> Any | None:
        try:
            return await self._get(f"/internal/case/{case_id}/legal-hypothesis")
        except CoreNotFoundError:
            return None

    # ------------------------------------------------------------------
    # Pipeline operator
    # ------------------------------------------------------------------

    async def get_pipeline_status(self) -> Any:
        return await self._get("/internal/pipeline/status")

    async def get_pipeline_capacity(self) -> Any:
        return await self._get("/internal/pipeline/capacity")

    async def trigger_full_pipeline(self) -> Any:
        return await self._post("/internal/pipeline/full")

    async def dispatch_next_pending(self) -> Any:
        return await self._post("/internal/pipeline/dispatch-next")

    async def yield_connector(self, connector: str) -> Any:
        return await self._post(f"/internal/ingest/{connector}/yield")


def _raise_for_status(response: httpx.Response) -> None:
    if response.status_code == 404:
        raise CoreNotFoundError("Not found in core service")
    if response.status_code >= 400:
        raise CoreServiceError(
            f"Core service error {response.status_code}: {response.text[:200]}"
        )
