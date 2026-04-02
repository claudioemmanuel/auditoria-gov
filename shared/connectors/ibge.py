"""Connector for IBGE (Instituto Brasileiro de Geografia e Estatística).

API: https://servicodados.ibge.gov.br/api
Auth: None (public open-data API).
Classification: ENRICHMENT_ONLY — provides reference data only (municipalities,
CNAE activity codes), never generates risk signals independently.

Jobs:
  ibge_municipios — full directory of ~5570 Brazilian municipalities.
  ibge_cnae       — CNAE economic activity sections and divisions.
"""
from typing import Optional

import httpx

from shared.connectors.base import BaseConnector, JobSpec, RateLimitPolicy, SourceClassification
from shared.connectors.http_client import ibge_client
from shared.logging import log
from shared.models.canonical import CanonicalEntity, NormalizeResult
from shared.models.raw import RawItem


class IBGEConnector(BaseConnector):
    """Connector for IBGE reference data (municipalities and CNAE codes)."""

    @property
    def name(self) -> str:
        return "ibge"

    @property
    def classification(self) -> SourceClassification:
        return SourceClassification.ENRICHMENT_ONLY

    def list_jobs(self) -> list[JobSpec]:
        return [
            JobSpec(
                name="ibge_municipios",
                description="Brazilian municipal directory (reference data)",
                domain="referencia",
                supports_incremental=False,
                enabled=True,
            ),
            JobSpec(
                name="ibge_cnae",
                description="CNAE economic activity sections and divisions (reference data)",
                domain="referencia",
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
        if job.name == "ibge_municipios":
            return await self._fetch_municipios(cursor)
        if job.name == "ibge_cnae":
            return await self._fetch_cnae(cursor)
        raise ValueError(f"Unknown IBGE job: {job.name}")

    async def _fetch_municipios(
        self, cursor: Optional[str]
    ) -> tuple[list[RawItem], Optional[str]]:
        # Single request — IBGE returns all ~5570 municipalities at once.
        if cursor is not None:
            # Already fetched; nothing more to do.
            return [], None

        try:
            async with ibge_client() as client:
                response = await client.get("/v1/localidades/municipios")
                response.raise_for_status()
                records: list[dict] = response.json()
        except httpx.HTTPError as exc:
            log.warning("ibge.municipios_fetch_error", error=str(exc))
            return [], None

        if not isinstance(records, list):
            log.warning("ibge.municipios_unexpected_response", type=type(records).__name__)
            return [], None

        items = [
            RawItem(raw_id=f"ibge_municipios:{r['id']}", data=r)
            for r in records
            if isinstance(r, dict) and "id" in r
        ]
        return items, None

    async def _fetch_cnae(
        self, cursor: Optional[str]
    ) -> tuple[list[RawItem], Optional[str]]:
        if cursor is not None:
            return [], None

        items: list[RawItem] = []

        async with ibge_client() as client:
            for resource, prefix in (
                ("/v2/cnae/secoes", "secao"),
                ("/v2/cnae/divisoes", "divisao"),
            ):
                try:
                    response = await client.get(resource)
                    response.raise_for_status()
                    records: list[dict] = response.json()
                except httpx.HTTPError as exc:
                    log.warning("ibge.cnae_fetch_error", resource=resource, error=str(exc))
                    continue

                if not isinstance(records, list):
                    log.warning(
                        "ibge.cnae_unexpected_response",
                        resource=resource,
                        type=type(records).__name__,
                    )
                    continue

                for r in records:
                    if not isinstance(r, dict) or "id" not in r:
                        continue
                    items.append(
                        RawItem(
                            raw_id=f"ibge_cnae:{prefix}:{r['id']}",
                            data={"_type": prefix, **r},
                        )
                    )

        return items, None

    def normalize(
        self,
        job: JobSpec,
        raw_items: list[RawItem],
        params: Optional[dict] = None,
    ) -> NormalizeResult:
        if job.name == "ibge_municipios":
            return self._normalize_municipios(raw_items)
        if job.name == "ibge_cnae":
            return self._normalize_cnae(raw_items)
        raise ValueError(f"Unknown IBGE job: {job.name}")

    def _normalize_municipios(self, raw_items: list[RawItem]) -> NormalizeResult:
        entities: list[CanonicalEntity] = []

        for item in raw_items:
            d = item.data
            try:
                micro = d.get("microrregiao") or {}
                meso = micro.get("mesorregiao") or {}
                uf = meso.get("UF") or {}
                regiao = uf.get("regiao") or {}

                entity = CanonicalEntity(
                    source_connector="ibge",
                    source_id=str(d["id"]),
                    type="municipio",
                    name=d.get("nome", ""),
                    identifiers={
                        "ibge_code": str(d["id"]),
                        "uf": uf.get("sigla", ""),
                    },
                    attrs={
                        "microrregiao": micro.get("nome", ""),
                        "mesorregiao": meso.get("nome", ""),
                        "uf_nome": uf.get("nome", ""),
                        "regiao_sigla": regiao.get("sigla", ""),
                        "regiao_nome": regiao.get("nome", ""),
                    },
                )
                entities.append(entity)
            except (KeyError, TypeError) as exc:
                log.warning("ibge.normalize_municipio_error", raw_id=item.raw_id, error=str(exc))

        return NormalizeResult(entities=entities)

    def _normalize_cnae(self, raw_items: list[RawItem]) -> NormalizeResult:
        entities: list[CanonicalEntity] = []

        for item in raw_items:
            d = item.data
            record_type = d.get("_type", "secao")
            entity_type = "cnae_section" if record_type == "secao" else "cnae_divisao"
            identifier_key = "cnae_secao" if record_type == "secao" else "cnae_divisao"

            try:
                entity = CanonicalEntity(
                    source_connector="ibge",
                    source_id=str(d["id"]),
                    type=entity_type,
                    name=d.get("descricao", ""),
                    identifiers={identifier_key: str(d["id"])},
                )
                entities.append(entity)
            except (KeyError, TypeError) as exc:
                log.warning("ibge.normalize_cnae_error", raw_id=item.raw_id, error=str(exc))

        return NormalizeResult(entities=entities)

    def rate_limit_policy(self) -> RateLimitPolicy:
        return RateLimitPolicy(requests_per_second=5, burst=10)
