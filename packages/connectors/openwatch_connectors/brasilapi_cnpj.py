"""Connector for BrasilAPI CNPJ enrichment lookups."""

from typing import Optional

import httpx

from openwatch_connectors.base import (
    BaseConnector,
    JobSpec,
    RateLimitPolicy,
    SourceClassification,
)
from openwatch_connectors.http_client import brasilapi_client
from shared.logging import log
from openwatch_models.canonical import (
    CanonicalEntity,
    CanonicalEvent,
    CanonicalEventParticipant,
    NormalizeResult,
)
from openwatch_models.raw import RawItem


def _normalize_cnpj(value: object) -> Optional[str]:
    digits = "".join(c for c in str(value or "") if c.isdigit())
    return digits if len(digits) == 14 else None


class BrasilAPICNPJConnector(BaseConnector):
    @property
    def name(self) -> str:
        return "brasilapi_cnpj"

    @property
    def classification(self) -> SourceClassification:
        return SourceClassification.ENRICHMENT_ONLY

    def list_jobs(self) -> list[JobSpec]:
        return [
            JobSpec(
                name="brasilapi_cnpj_lookup",
                description="CNPJ profile lookup via BrasilAPI",
                domain="empresa",
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
        if job.name != "brasilapi_cnpj_lookup":
            raise ValueError(f"Unknown BrasilAPI CNPJ job: {job.name}")
        if cursor is not None:
            return [], None

        cnpj = _normalize_cnpj((params or {}).get("cnpj"))
        if cnpj is None:
            return [], None

        try:
            async with brasilapi_client() as client:
                response = await client.get(f"/api/cnpj/v1/{cnpj}")
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPError as exc:
            log.warning("brasilapi_cnpj.fetch_error", cnpj=cnpj, error=str(exc))
            return [], None

        if not isinstance(payload, dict):
            log.warning(
                "brasilapi_cnpj.unexpected_response",
                cnpj=cnpj,
                type=type(payload).__name__,
            )
            return [], None

        return [
            RawItem(
                raw_id=f"{job.name}:{cnpj}",
                data={"cnpj": cnpj, **payload},
            )
        ], None

    def normalize(
        self,
        job: JobSpec,
        raw_items: list[RawItem],
        params: Optional[dict] = None,
    ) -> NormalizeResult:
        if job.name != "brasilapi_cnpj_lookup":
            raise ValueError(f"Unknown BrasilAPI CNPJ job: {job.name}")

        entities: list[CanonicalEntity] = []
        events: list[CanonicalEvent] = []

        for item in raw_items:
            d = item.data
            cnpj = _normalize_cnpj(d.get("cnpj"))
            if cnpj is None:
                continue

            company = CanonicalEntity(
                source_connector="brasilapi_cnpj",
                source_id=cnpj,
                type="company",
                name=(d.get("razao_social") or d.get("nome_fantasia") or f"CNPJ {cnpj}"),
                identifiers={"cnpj": cnpj},
            )
            entities.append(company)

            address_parts = [
                str(d.get("logradouro") or "").strip(),
                str(d.get("numero") or "").strip(),
                str(d.get("complemento") or "").strip(),
                str(d.get("bairro") or "").strip(),
                str(d.get("cep") or "").strip(),
            ]
            endereco = ", ".join(part for part in address_parts if part)

            cnae_code = d.get("cnae_fiscal") or d.get("codigo_cnae_fiscal")
            cnae_desc = d.get("cnae_fiscal_descricao")
            cnae = cnae_code if not cnae_desc else f"{cnae_code} - {cnae_desc}"

            events.append(
                CanonicalEvent(
                    source_connector="brasilapi_cnpj",
                    source_id=f"{item.raw_id}:registration_status",
                    type="company_profile",
                    subtype="registration_status",
                    attrs={
                        "situacao_cadastral": (
                            d.get("descricao_situacao_cadastral")
                            or d.get("situacao_cadastral")
                        ),
                        "cnae": cnae,
                        "porte": d.get("porte"),
                        "natureza_juridica": d.get("natureza_juridica"),
                        "capital_social": d.get("capital_social"),
                        "endereco": endereco,
                        "uf": d.get("uf"),
                        "municipio": d.get("municipio"),
                    },
                    participants=[
                        CanonicalEventParticipant(
                            entity_ref=company,
                            role="subject",
                        )
                    ],
                )
            )

        return NormalizeResult(entities=entities, events=events)

    def rate_limit_policy(self) -> RateLimitPolicy:
        return RateLimitPolicy(requests_per_second=5, burst=10)
