"""Connector for Bacen — Banco Central do Brasil (SGS time-series API).

API: https://api.bcb.gov.br
Auth: None (public open-data API).
Classification: ENRICHMENT_ONLY — provides economic reference data only
(Selic, IPCA, PTAX), never generates risk signals independently.

Jobs:
  bacen_selic  — Selic interest rate (series 432).
  bacen_ipca   — IPCA monthly inflation (series 433).
  bacen_cambio — USD/BRL PTAX sell rate (series 3698).
"""

from datetime import datetime, timezone
from typing import Optional

import httpx

from openwatch_connectors.base import (
    BaseConnector,
    JobSpec,
    RateLimitPolicy,
    SourceClassification,
)
from openwatch_connectors.http_client import bacen_client
from openwatch_utils.logging import log
from openwatch_models.canonical import CanonicalEvent, NormalizeResult
from openwatch_models.raw import RawItem

_SERIES_MAP: dict[str, dict] = {
    "bacen_selic": {"codigo": 432, "subtype": "selic", "desc": "Selic interest rate"},
    "bacen_ipca": {"codigo": 433, "subtype": "ipca", "desc": "IPCA monthly inflation"},
    "bacen_cambio": {"codigo": 3698, "subtype": "cambio", "desc": "USD/BRL PTAX sell rate"},
}

_LAST_N = 365


def _parse_bacen_date(value: object) -> Optional[datetime]:
    """Parse Bacen date formats: DD/MM/YYYY, YYYY-MM-DD, or ISO."""
    if not value:
        return None
    raw = str(value).strip()
    if not raw:
        return None

    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"):
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


class BacenConnector(BaseConnector):
    """Connector for Banco Central do Brasil (SGS time-series)."""

    @property
    def name(self) -> str:
        return "bacen"

    @property
    def classification(self) -> SourceClassification:
        return SourceClassification.ENRICHMENT_ONLY

    def list_jobs(self) -> list[JobSpec]:
        return [
            JobSpec(
                name="bacen_selic",
                description="Selic interest rate series (code 432)",
                domain="indicador_economico",
                supports_incremental=False,
                enabled=True,
            ),
            JobSpec(
                name="bacen_ipca",
                description="IPCA monthly inflation series (code 433)",
                domain="indicador_economico",
                supports_incremental=False,
                enabled=True,
            ),
            JobSpec(
                name="bacen_cambio",
                description="USD/BRL PTAX sell rate (code 3698)",
                domain="indicador_economico",
                supports_incremental=False,
                enabled=True,
            ),
        ]

    async def fetch(
        self,
        job: JobSpec,
        cursor: Optional[str] = None,
        params: Optional[dict] = None,
    ) -> tuple[list[RawItem], Optional[str]]:
        # Full dump each time — no pagination / incremental cursor.
        if cursor is not None:
            return [], None

        spec = _SERIES_MAP.get(job.name)
        if not spec:
            raise ValueError(f"Unknown Bacen job: {job.name}")

        codigo = spec["codigo"]
        endpoint = f"/dados/serie/bcdata.sgs/{codigo}/dados/ultimos/{_LAST_N}"

        try:
            async with bacen_client() as client:
                response = await client.get(
                    endpoint,
                    params={"formato": "json"},
                )
                response.raise_for_status()
                records: list[dict] = response.json()
        except httpx.HTTPError as exc:
            log.warning("bacen.fetch_error", job=job.name, codigo=codigo, error=str(exc))
            return [], None

        if not isinstance(records, list):
            log.warning("bacen.unexpected_response", job=job.name, type=type(records).__name__)
            return [], None

        items = [
            RawItem(
                raw_id=f"{job.name}:{r.get('data', i)}",
                data={"_codigo": codigo, "_subtype": spec["subtype"], **r},
            )
            for i, r in enumerate(records)
            if isinstance(r, dict)
        ]

        log.info("bacen.fetched", job=job.name, codigo=codigo, count=len(items))
        return items, None

    def normalize(
        self,
        job: JobSpec,
        raw_items: list[RawItem],
        params: Optional[dict] = None,
    ) -> NormalizeResult:
        events: list[CanonicalEvent] = []

        for item in raw_items:
            d = item.data
            try:
                valor_raw = d.get("valor")
                valor = float(valor_raw) if valor_raw not in (None, "", "-") else None

                events.append(
                    CanonicalEvent(
                        source_connector="bacen",
                        source_id=item.raw_id,
                        type="indicador_economico",
                        subtype=d.get("_subtype", ""),
                        occurred_at=_parse_bacen_date(d.get("data")),
                        attrs={
                            "codigo_serie": d.get("_codigo"),
                            "valor": valor,
                            "data": d.get("data", ""),
                        },
                    )
                )
            except (KeyError, TypeError, ValueError) as exc:
                log.warning("bacen.normalize_error", raw_id=item.raw_id, error=str(exc))

        return NormalizeResult(events=events)

    def rate_limit_policy(self) -> RateLimitPolicy:
        return RateLimitPolicy(requests_per_second=10, burst=20)
