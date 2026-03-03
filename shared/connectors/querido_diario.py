"""Querido Diário Connector — Municipal gazette entries.

API: https://queridodiario.ok.org.br/api/gazettes (public, no auth)
Provides full-text search of Brazilian municipal official gazettes.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

import asyncio

import httpx

from shared.connectors.base import BaseConnector, JobSpec, RateLimitPolicy
from shared.models.canonical import (
    CanonicalEntity,
    CanonicalEvent,
    NormalizeResult,
)
from shared.models.raw import RawItem


_BASE_URL = "https://api.queridodiario.ok.org.br"


class QueridoDiarioConnector(BaseConnector):
    """Connector for Querido Diário municipal gazette API."""

    @property
    def name(self) -> str:
        return "querido_diario"

    def list_jobs(self) -> list[JobSpec]:
        return [
            JobSpec(
                name="qd_gazettes",
                description="Municipal gazette entries",
                domain="diario_oficial",
                supports_incremental=True,
                enabled=True,
            ),
        ]

    def rate_limit_policy(self) -> RateLimitPolicy:
        return RateLimitPolicy(requests_per_second=1, burst=2)

    async def fetch(
        self,
        job: JobSpec,
        cursor: Optional[str] = None,
        params: Optional[dict] = None,
    ) -> tuple[list[RawItem], Optional[str]]:
        """Fetch gazette entries from Querido Diário API.

        cursor format: "offset:YYYY-MM-DD" (offset + published_since date)
        """
        offset = 0
        published_since = (datetime.now(timezone.utc) - timedelta(days=1825)).strftime("%Y-%m-%d")

        if params and params.get("published_since"):
            published_since = str(params["published_since"])

        if cursor:
            parts = cursor.split(":", 1)
            offset = int(parts[0])
            if len(parts) > 1:
                published_since = parts[1]

        page_size = 100

        async with httpx.AsyncClient(timeout=30) as client:
            for attempt in range(4):
                response = await client.get(
                    f"{_BASE_URL}/gazettes",
                    params={
                        "published_since": published_since,
                        "offset": offset,
                        "size": page_size,
                        "sort_by": "relevance",
                    },
                )
                if response.status_code == 429:
                    wait = 2 ** (attempt + 1)  # 2, 4, 8, 16 seconds
                    await asyncio.sleep(wait)
                    continue
                response.raise_for_status()
                break
            else:
                response.raise_for_status()  # raise the 429 after all retries
            data = {} if response.status_code == 204 else response.json()

        gazettes = data.get("gazettes", [])
        total = data.get("total_gazettes", 0)

        items: list[RawItem] = []
        for g in gazettes:
            raw_id = g.get("territory_id", "") + ":" + g.get("date", "") + ":" + str(g.get("edition", ""))
            items.append(RawItem(raw_id=raw_id, data=g))

        # Next cursor
        next_offset = offset + len(items)
        if next_offset < total and items:
            next_cursor = f"{next_offset}:{published_since}"
        else:
            next_cursor = None

        return items, next_cursor

    def normalize(
        self,
        job: JobSpec,
        raw_items: list[RawItem],
        params: Optional[dict] = None,
    ) -> NormalizeResult:
        entities: list[CanonicalEntity] = []
        events: list[CanonicalEvent] = []

        for item in raw_items:
            data = item.data
            territory_id = data.get("territory_id", "")
            territory_name = data.get("territory_name", "")
            state_code = data.get("state_code", "")
            date = data.get("date", "")
            excerpts = data.get("excerpts", [])
            url = data.get("url", "")

            # Create entity for the municipality
            if territory_name:
                entities.append(
                    CanonicalEntity(
                        source_connector="querido_diario",
                        source_id=f"qd_territory:{territory_id}",
                        type="org",
                        name=f"Prefeitura de {territory_name}/{state_code}",
                        identifiers={"territory_id": territory_id},
                        attrs={
                            "state_code": state_code,
                            "territory_name": territory_name,
                        },
                    )
                )

            # Create event for each gazette entry
            occurred_at = None
            if date:
                try:
                    occurred_at = datetime.fromisoformat(date)
                except (ValueError, TypeError):
                    pass

            excerpt_text = " ".join(excerpts[:3]) if excerpts else ""
            content_preview = excerpt_text[:1000] if excerpt_text else ""

            events.append(
                CanonicalEvent(
                    source_connector="querido_diario",
                    source_id=item.raw_id,
                    type="diario_oficial",
                    subtype="gazette",
                    description=content_preview,
                    occurred_at=occurred_at,
                    attrs={
                        "territory_id": territory_id,
                        "territory_name": territory_name,
                        "state_code": state_code,
                        "url": url,
                        "edition": data.get("edition"),
                        "is_extra_edition": data.get("is_extra_edition", False),
                        "excerpt_count": len(excerpts),
                    },
                )
            )

        return NormalizeResult(entities=entities, events=events)
