"""Connector for Transfere.gov.br (formerly SICONV).

APIs are module-specific (PostgREST):
  - TED: https://api.transferegov.gestao.gov.br/ted/
  - Transferências Especiais: https://api.transferegov.gestao.gov.br/transferenciasespeciais/
Docs: https://docs.api.transferegov.gestao.gov.br/{module}/
Auth: None (public open-data API).
Pagination: PostgREST Range headers.
"""

from datetime import datetime, timezone
from typing import Optional

from shared.connectors.base import BaseConnector, JobSpec, RateLimitPolicy
from shared.connectors.http_client import transferegov_client, DEFAULT_PAGE_SIZE
from shared.models.canonical import (
    CanonicalEntity,
    CanonicalEvent,
    CanonicalEventParticipant,
    NormalizeResult,
)
from shared.models.raw import RawItem

# Module paths and their PostgREST table endpoints
_JOB_CONFIG: dict[str, dict] = {
    "transferegov_ted": {
        "module": "ted",
        "endpoint": "/termo_execucao",
        "description": "TED — Termos de Execução Descentralizada",
        "domain": "transferencia",
    },
    "transferegov_transferencias_especiais": {
        "module": "transferenciasespeciais",
        "endpoint": "/plano_acao_especial",
        "description": "Special transfers (emendas parlamentares)",
        "domain": "transferencia",
    },
}


class TransfereGovConnector(BaseConnector):
    """Connector for Transfere.gov.br (PostgREST open-data APIs)."""

    @property
    def name(self) -> str:
        return "transferegov"

    def list_jobs(self) -> list[JobSpec]:
        return [
            JobSpec(
                name=name,
                description=cfg["description"],
                domain=cfg["domain"],
                enabled=True,
            )
            for name, cfg in _JOB_CONFIG.items()
        ]

    async def fetch(
        self,
        job: JobSpec,
        cursor: Optional[str] = None,
        params: Optional[dict] = None,
    ) -> tuple[list[RawItem], Optional[str]]:
        cfg = _JOB_CONFIG.get(job.name)
        if not cfg:
            raise ValueError(f"Unknown job: {job.name}")

        offset = int(cursor) if cursor else 0
        limit = DEFAULT_PAGE_SIZE

        # PostgREST uses Range header for pagination
        headers = {
            "Range-Unit": "items",
            "Range": f"{offset}-{offset + limit - 1}",
        }

        query_params: dict = {}
        if params:
            query_params.update(params)

        async with transferegov_client(cfg["module"]) as client:
            response = await client.get(
                cfg["endpoint"],
                params=query_params,
                headers=headers,
            )
            response.raise_for_status()
            body = [] if response.status_code == 204 else response.json()

        records = body if isinstance(body, list) else body.get("data", body.get("registros", []))
        items = [
            RawItem(raw_id=f"{job.name}:{offset}:{i}", data=r)
            for i, r in enumerate(records)
        ]
        next_cursor = str(offset + len(records)) if len(records) >= limit else None
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

            if job.name == "transferegov_transferencias_especiais":
                cnpj = d.get("cnpj_beneficiario_plano_acao", "")
                nome = d.get("nome_beneficiario_plano_acao", "")
                beneficiario = CanonicalEntity(
                    source_connector="transferegov",
                    source_id=cnpj or str(d.get("id_plano_acao", item.raw_id)),
                    type="org",
                    name=nome or "Beneficiário não informado",
                    identifiers={"cnpj": cnpj} if cnpj else {},
                    attrs={"uf": d.get("uf_beneficiario_plano_acao", "")},
                )
                entities.append(beneficiario)

                value_brl = _sum_money_fields(
                    d.get("valor_investimento_plano_acao"),
                    d.get("valor_custeio_plano_acao"),
                )
                occurred_at = (
                    _parse_any_datetime(
                        d.get("data_plano_acao")
                        or d.get("data_cadastro_plano_acao")
                    )
                    or _parse_year(d.get("ano_plano_acao"))
                )
                events.append(
                    CanonicalEvent(
                        source_connector="transferegov",
                        source_id=item.raw_id,
                        type="transferencia",
                        subtype=job.name,
                        description=d.get(
                            "codigo_descricao_areas_politicas_publicas_plano_acao", ""
                        ),
                        occurred_at=occurred_at,
                        value_brl=value_brl,
                        attrs={
                            "situacao": d.get("situacao_plano_acao", ""),
                            "codigo_plano_acao": d.get("codigo_plano_acao", ""),
                            "ano_plano_acao": d.get("ano_plano_acao"),
                            "parlamentar": d.get("nome_parlamentar_emenda_plano_acao", ""),
                            "uf": d.get("uf_beneficiario_plano_acao", ""),
                        },
                        participants=[
                            CanonicalEventParticipant(
                                entity_ref=beneficiario,
                                role="beneficiario",
                            )
                        ],
                    )
                )
                continue

            # transferegov_ted via /termo_execucao
            plano_id = d.get("id_plano_acao")
            beneficiario = CanonicalEntity(
                source_connector="transferegov",
                source_id=f"plano_acao:{plano_id or item.raw_id}",
                type="org",
                name=f"Plano de Acao {plano_id}" if plano_id else "Plano de Acao",
                identifiers={},
            )
            entities.append(beneficiario)

            events.append(
                CanonicalEvent(
                    source_connector="transferegov",
                    source_id=item.raw_id,
                    type="transferencia",
                    subtype=job.name,
                    description=d.get("tx_situacao_termo", "Termo de execucao TED"),
                    occurred_at=_parse_any_datetime(
                        d.get("dt_assinatura_termo") or d.get("dt_efetivacao_termo")
                    ),
                    value_brl=_sum_money_fields(
                        d.get("vl_total_convenio"),
                        d.get("vl_repasse_convenio"),
                        d.get("vl_global_convenio"),
                        d.get("vl_global_termo"),
                        d.get("valor_global"),
                    ),
                    attrs={
                        "id_termo": d.get("id_termo"),
                        "id_plano_acao": plano_id,
                        "numero_ns_termo": d.get("tx_numero_ns_termo"),
                        "situacao_termo": d.get("tx_situacao_termo"),
                        "data_assinatura_termo": d.get("dt_assinatura_termo"),
                        "data_efetivacao_termo": d.get("dt_efetivacao_termo"),
                        "uf": d.get("sg_uf", d.get("uf", "")),
                    },
                    participants=[
                        CanonicalEventParticipant(
                            entity_ref=beneficiario,
                            role="beneficiario",
                        )
                    ],
                )
            )

        return NormalizeResult(entities=entities, events=events)


def _sum_money_fields(*values: object) -> Optional[float]:
    total = 0.0
    has_value = False
    for raw in values:
        if raw in (None, ""):
            continue
        try:
            total += float(raw)
            has_value = True
        except (TypeError, ValueError):
            continue
    return total if has_value else None


def _parse_any_datetime(value: object) -> Optional[datetime]:
    if not value:
        return None
    raw = str(value).strip()
    if not raw:
        return None

    for fmt in (
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%d/%m/%Y",
        "%Y%m%d",
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


def _parse_year(value: object) -> Optional[datetime]:
    if value is None:
        return None
    raw = str(value).strip()
    if len(raw) == 4 and raw.isdigit():
        return datetime(int(raw), 1, 1, tzinfo=timezone.utc)
    return None
