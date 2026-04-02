"""Connector for Jurisprudência — Higher Court Rulings (STF/STJ).

Covers:
  - STF (Supremo Tribunal Federal): Supreme Court rulings via search API.
  - STJ: planned for future (HTML/JSONP response requires complex parsing).

Pagination:
  - Page-based (page param in POST body).
  - Cursor = str(page_number), starting at 1.
  - next_cursor = str(page + 1) if len(results) >= pageSize else None.
  - Page size: 25.
"""

from datetime import datetime, timezone
from typing import Optional

import httpx
import structlog

from shared.connectors.base import BaseConnector, JobSpec, RateLimitPolicy
from shared.connectors.http_client import jurisprudencia_stf_client
from shared.models.canonical import CanonicalEvent, NormalizeResult
from shared.models.raw import RawItem

log = structlog.get_logger(__name__)

_STF_PAGE_SIZE = 25

# Job-specific search queries
_JOB_QUERIES: dict[str, str] = {
    "juris_stf_licitacao": "licitação fraude OR irregularidade",
    "juris_stf_improbidade": "improbidade administrativa",
}


def _parse_date(value: object) -> Optional[datetime]:
    """Parse a date string from STF API into a UTC datetime."""
    if not value:
        return None
    raw = str(value).strip()
    if not raw:
        return None

    for fmt in (
        "%d/%m/%Y",
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
    ):
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        return None


class JurisprudenciaConnector(BaseConnector):
    """Connector for Jurisprudência — Higher Court Rulings (STF)."""

    @property
    def name(self) -> str:
        return "jurisprudencia"

    def list_jobs(self) -> list[JobSpec]:
        return [
            JobSpec(
                name="juris_stf_licitacao",
                description="STF rulings on procurement fraud",
                domain="jurisprudencia",
                enabled=True,
            ),
            JobSpec(
                name="juris_stf_improbidade",
                description="STF rulings on administrative improbity",
                domain="jurisprudencia",
                enabled=True,
            ),
        ]

    async def fetch(
        self,
        job: JobSpec,
        cursor: Optional[str] = None,
        params: Optional[dict] = None,
    ) -> tuple[list[RawItem], Optional[str]]:
        query = _JOB_QUERIES.get(job.name)
        if query is None:
            raise ValueError(f"Unknown jurisprudencia job: {job.name}")

        page = int(cursor) if cursor else 1
        return await self._fetch_stf(job.name, query, page)

    async def _fetch_stf(
        self, job_name: str, query: str, page: int
    ) -> tuple[list[RawItem], Optional[str]]:
        payload = {
            "query": query,
            "base": "acordaos",
            "page": page,
            "pageSize": _STF_PAGE_SIZE,
        }

        log.info(
            "jurisprudencia.stf.fetch",
            job=job_name,
            query=query,
            page=page,
        )

        try:
            async with jurisprudencia_stf_client() as client:
                response = await client.post(
                    "/api/search/pesquisar",
                    json=payload,
                )
                response.raise_for_status()
                body: dict = response.json() or {}
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status in (429, 503):
                log.warning(
                    "jurisprudencia.stf.rate_limited",
                    status=status,
                    page=page,
                    job=job_name,
                )
                # Return current cursor so the orchestrator can resume later
                return [], str(page)
            raise
        except httpx.HTTPError as exc:
            log.error(
                "jurisprudencia.stf.http_error",
                error=str(exc),
                page=page,
                job=job_name,
            )
            # Return current cursor for resume on transient errors
            return [], str(page)

        results: list[dict] = body.get("result", []) if body else []
        items = [
            RawItem(raw_id=f"{job_name}:{page}:{i}", data=r)
            for i, r in enumerate(results)
        ]

        next_cursor = (
            str(page + 1) if len(results) >= _STF_PAGE_SIZE else None
        )

        log.info(
            "jurisprudencia.stf.fetched",
            job=job_name,
            page=page,
            count=len(results),
            has_next=next_cursor is not None,
        )

        return items, next_cursor

    def normalize(
        self,
        job: JobSpec,
        raw_items: list[RawItem],
        params: Optional[dict] = None,
    ) -> NormalizeResult:
        events: list[CanonicalEvent] = []

        for item in raw_items:
            d = item.data
            ementa = (d.get("ementa") or "").strip() or None
            relator = (d.get("relator") or "").strip()
            numero_processo = (d.get("numeroProcesso") or d.get("id") or "").strip()
            classe = (d.get("classe") or "").strip()
            url = (d.get("url") or "").strip() or None

            event = CanonicalEvent(
                source_connector="jurisprudencia",
                source_id=item.raw_id,
                type="jurisprudencia",
                subtype="acordao_stf",
                description=ementa,
                occurred_at=_parse_date(d.get("dataPublicacao")),
                attrs={
                    "tribunal": "STF",
                    "relator": relator,
                    "numero_processo": numero_processo,
                    "classe": classe,
                    "url": url,
                },
            )
            events.append(event)

        return NormalizeResult(events=events)

    def rate_limit_policy(self) -> RateLimitPolicy:
        return RateLimitPolicy(requests_per_second=1, burst=3)
