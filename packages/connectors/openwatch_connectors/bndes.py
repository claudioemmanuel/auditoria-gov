"""Connector for BNDES — Banco Nacional de Desenvolvimento Econômico e Social.

API: https://dadosabertos.bndes.gov.br/api/3/action (CKAN datastore)
Auth: None (public open-data API).
Classification: FULL_SOURCE — financing operations can generate risk signals.

Jobs:
  bndes_operacoes_auto     — Automatic financing operations.
  bndes_operacoes_nao_auto — Non-automatic financing operations.
"""

from datetime import datetime, timezone
from typing import Optional

import httpx

from openwatch_connectors.base import BaseConnector, JobSpec, RateLimitPolicy
from openwatch_connectors.http_client import bndes_client
from openwatch_utils.logging import log
from openwatch_models.canonical import (
    CanonicalEntity,
    CanonicalEvent,
    CanonicalEventParticipant,
    NormalizeResult,
)
from openwatch_models.raw import RawItem

_PAGE_SIZE = 100

_RESOURCE_MAP: dict[str, dict] = {
    "bndes_operacoes_auto": {
        "resource_id": "612faa0b-b6be-4b2c-9317-da5dc2c0b901",
        "subtype": "automatica",
        "desc": "Automatic financing operations",
    },
    "bndes_operacoes_nao_auto": {
        "resource_id": "6f56b78c-510f-44b6-8274-78a5b7e931f4",
        "subtype": "nao_automatica",
        "desc": "Non-automatic financing operations",
    },
}


def _parse_bndes_date(value: object) -> Optional[datetime]:
    """Parse BNDES date formats: YYYY-MM-DD, DD/MM/YYYY, or ISO."""
    if not value:
        return None
    raw = str(value).strip()
    if not raw:
        return None

    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S"):
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


class BNDESConnector(BaseConnector):
    """Connector for BNDES open-data (CKAN datastore)."""

    @property
    def name(self) -> str:
        return "bndes"

    def list_jobs(self) -> list[JobSpec]:
        return [
            JobSpec(
                name="bndes_operacoes_auto",
                description="BNDES automatic financing operations",
                domain="financiamento_bndes",
                supports_incremental=True,
                enabled=True,
            ),
            JobSpec(
                name="bndes_operacoes_nao_auto",
                description="BNDES non-automatic financing operations",
                domain="financiamento_bndes",
                supports_incremental=True,
                enabled=True,
            ),
        ]

    async def fetch(
        self,
        job: JobSpec,
        cursor: Optional[str] = None,
        params: Optional[dict] = None,
    ) -> tuple[list[RawItem], Optional[str]]:
        spec = _RESOURCE_MAP.get(job.name)
        if not spec:
            raise ValueError(f"Unknown BNDES job: {job.name}")

        offset = int(cursor) if cursor else 0

        query_params: dict = {
            "resource_id": spec["resource_id"],
            "limit": _PAGE_SIZE,
            "offset": offset,
        }

        try:
            async with bndes_client() as client:
                response = await client.get("/datastore_search", params=query_params)
                response.raise_for_status()
                body = response.json()
        except httpx.HTTPError as exc:
            log.warning("bndes.fetch_error", job=job.name, offset=offset, error=str(exc))
            return [], None

        result = body.get("result", {})
        records = result.get("records", [])
        total = result.get("total", 0)

        if not isinstance(records, list):
            log.warning("bndes.unexpected_response", job=job.name, type=type(records).__name__)
            return [], None

        items = [
            RawItem(
                raw_id=f"{job.name}:{offset + i}:{r.get('_id', i)}",
                data={"_subtype": spec["subtype"], **r},
            )
            for i, r in enumerate(records)
            if isinstance(r, dict)
        ]

        next_offset = offset + _PAGE_SIZE
        next_cursor = str(next_offset) if next_offset < total else None

        log.info(
            "bndes.fetched",
            job=job.name,
            offset=offset,
            count=len(items),
            total=total,
        )
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
            d = item.data
            try:
                # Entity: borrower company
                cnpj = str(d.get("cnpj") or d.get("cliente") or "").strip()
                company_name = str(d.get("cliente") or d.get("cnpj") or "").strip()

                company = CanonicalEntity(
                    source_connector="bndes",
                    source_id=cnpj or item.raw_id,
                    type="company",
                    name=company_name,
                    identifiers={"cnpj": cnpj} if cnpj else {},
                )
                entities.append(company)

                # Value
                valor_raw = (
                    d.get("valor_da_operacao_em_reais")
                    or d.get("valor_contratado_reais")
                )
                value_brl: Optional[float] = None
                if valor_raw not in (None, "", "-"):
                    try:
                        value_brl = float(valor_raw)
                    except (ValueError, TypeError):
                        pass

                events.append(
                    CanonicalEvent(
                        source_connector="bndes",
                        source_id=item.raw_id,
                        type="financiamento_bndes",
                        subtype=d.get("_subtype", ""),
                        occurred_at=_parse_bndes_date(d.get("data_da_contratacao")),
                        value_brl=value_brl,
                        attrs={
                            "uf": d.get("uf", ""),
                            "setor_cnae": d.get("setor_cnae", ""),
                            "porte_do_cliente": d.get("porte_do_cliente", ""),
                            "instrumento_financeiro": d.get("instrumento_financeiro", ""),
                            "produto": d.get("produto", ""),
                        },
                        participants=[
                            CanonicalEventParticipant(
                                entity_ref=company,
                                role="borrower",
                            ),
                        ],
                    )
                )
            except (KeyError, TypeError, ValueError) as exc:
                log.warning("bndes.normalize_error", raw_id=item.raw_id, error=str(exc))

        return NormalizeResult(entities=entities, events=events)

    def rate_limit_policy(self) -> RateLimitPolicy:
        return RateLimitPolicy(requests_per_second=5, burst=10)
