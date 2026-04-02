"""
Core Service Gateway Client

This module provides the API gateway pattern for the post-split architecture.
After the open-core split, the public API must NEVER import core logic directly.
Instead, all computation is delegated to the private core service via this client.

Usage (post-split public repo only):
    from api.core_client import CoreClient

    client = CoreClient()
    signals = await client.get_signals(entity_id="...", filters=...)

Configuration:
    CORE_SERVICE_URL — internal URL of the openwatch-core API service
    CORE_API_KEY     — service-to-service authentication token

IMPORTANT: This file is intentionally a stub in the monorepo.
           It becomes the primary integration point in the public repo post-split.
"""
from __future__ import annotations

import httpx
from shared.config import settings


class CoreServiceError(Exception):
    """Raised when the core service returns an error."""


class CoreClient:
    """
    Async HTTP client for the openwatch-core internal service.

    In the post-split architecture:
    - openwatch (public) → calls CoreClient → openwatch-core (private)
    - openwatch-core runs computation and returns filtered results
    - No core logic ever executes in the public layer

    All methods map 1:1 to internal API endpoints in openwatch-core.
    """

    def __init__(self) -> None:
        self._base_url = settings.CORE_SERVICE_URL
        self._api_key = settings.CORE_API_KEY
        self._timeout = httpx.Timeout(30.0, connect=5.0)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "X-Service": "openwatch-public",
        }

    async def get_radar(self, **params: object) -> dict:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            r = await client.get(
                f"{self._base_url}/internal/radar",
                headers=self._headers(),
                params=params,  # type: ignore[arg-type]
            )
            self._raise_for_status(r)
            return r.json()

    async def get_case(self, case_id: str) -> dict:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            r = await client.get(
                f"{self._base_url}/internal/case/{case_id}",
                headers=self._headers(),
            )
            self._raise_for_status(r)
            return r.json()

    async def get_entity(self, entity_id: str) -> dict:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            r = await client.get(
                f"{self._base_url}/internal/entity/{entity_id}",
                headers=self._headers(),
            )
            self._raise_for_status(r)
            return r.json()

    async def search_entities(self, q: str, entity_type: str | None = None, limit: int = 20) -> list[dict]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            r = await client.get(
                f"{self._base_url}/internal/entity/search",
                headers=self._headers(),
                params={"q": q, "type": entity_type, "limit": limit},
            )
            self._raise_for_status(r)
            return r.json()

    async def get_signal_provenance(self, signal_id: str) -> dict:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            r = await client.get(
                f"{self._base_url}/internal/signal/{signal_id}/provenance",
                headers=self._headers(),
            )
            self._raise_for_status(r)
            return r.json()

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        if response.status_code >= 500:
            raise CoreServiceError(f"Core service error: {response.status_code}")
        if response.status_code == 404:
            raise CoreServiceError("Not found in core service")
        if response.status_code >= 400:
            raise CoreServiceError(f"Core service request error: {response.status_code} — {response.text[:200]}")
