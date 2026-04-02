"""Connector for TCE-RJ — Tribunal de Contas do Estado do Rio de Janeiro.

Covers:
  - Licitações: Municipal procurement/auctions in RJ state.
  - Contratos: Municipal contracts in RJ state.
  - Penalidades: Penalties and refund orders.

Pagination:
  - Offset-based, page_size=100. Cursor = str(offset).
  When len(returned items) < page_size -> no next cursor.
"""

from datetime import datetime, timezone
from typing import Optional

import httpx

from shared.connectors.base import BaseConnector, JobSpec, RateLimitPolicy
from shared.connectors.http_client import tce_rj_client
from shared.models.canonical import (
    CanonicalEntity,
    CanonicalEvent,
    CanonicalEventParticipant,
    NormalizeResult,
)
from shared.models.raw import RawItem

_PAGE_SIZE = 100


def _parse_any_datetime(value: object) -> Optional[datetime]:
    """Parse various datetime formats returned by TCE-RJ into UTC datetimes."""
    if not value:
        return None
    raw = str(value).strip()
    if not raw:
        return None

    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d %H:%M:%S", "%Y%m%d"):
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


def _clean(value: object) -> Optional[str]:
    """Return stripped string or None."""
    if not value:
        return None
    s = str(value).strip()
    return s or None


def _cnpj_entity(
    cnpj: str,
    name: str,
    *,
    source_connector: str = "tce_rj",
) -> CanonicalEntity:
    """Build a company CanonicalEntity from a CNPJ."""
    return CanonicalEntity(
        source_connector=source_connector,
        source_id=cnpj,
        type="company",
        name=name,
        identifiers={"cnpj": cnpj},
    )


class TCERJConnector(BaseConnector):
    """TCE-RJ open-data connector."""

    @property
    def name(self) -> str:
        return "tce_rj"

    def list_jobs(self) -> list[JobSpec]:
        return [
            JobSpec(
                name="tce_rj_licitacoes",
                description="Municipal procurement/auctions in RJ state",
                domain="licitacao",
                enabled=True,
            ),
            JobSpec(
                name="tce_rj_contratos",
                description="Municipal contracts in RJ state",
                domain="contrato",
                enabled=True,
            ),
            JobSpec(
                name="tce_rj_penalidades",
                description="Penalties and refund orders in RJ state",
                domain="penalidade_tce_rj",
                enabled=True,
            ),
        ]

    # ------------------------------------------------------------------
    # fetch
    # ------------------------------------------------------------------

    async def fetch(
        self,
        job: JobSpec,
        cursor: Optional[str] = None,
        params: Optional[dict] = None,
    ) -> tuple[list[RawItem], Optional[str]]:
        offset = int(cursor) if cursor else 0

        if job.name == "tce_rj_licitacoes":
            return await self._fetch_endpoint("/licitacoes", "tce_rj_licitacoes", offset, params)
        if job.name == "tce_rj_contratos":
            return await self._fetch_endpoint("/contratos_municipio", "tce_rj_contratos", offset, params)
        if job.name == "tce_rj_penalidades":
            return await self._fetch_endpoint("/penalidades_ressarcimento_municipio", "tce_rj_penalidades", offset, params)

        raise ValueError(f"Unknown TCE-RJ job: {job.name}")

    async def _fetch_endpoint(
        self,
        path: str,
        job_name: str,
        offset: int,
        params: Optional[dict] = None,
    ) -> tuple[list[RawItem], Optional[str]]:
        query: dict[str, object] = {
            "inicio": offset,
            "limite": _PAGE_SIZE,
        }
        if params:
            if "exercicio" in params:
                query["exercicio"] = params["exercicio"]

        async with tce_rj_client() as client:
            response = await client.get(path, params=query)
            response.raise_for_status()
            body = response.json()

        items_data: list[dict] = body if isinstance(body, list) else (body.get("items", []) if isinstance(body, dict) else [])
        items = [
            RawItem(raw_id=f"{job_name}:{offset}:{i}", data=r)
            for i, r in enumerate(items_data)
        ]
        next_cursor = (
            str(offset + _PAGE_SIZE)
            if len(items_data) >= _PAGE_SIZE
            else None
        )
        return items, next_cursor

    # ------------------------------------------------------------------
    # normalize
    # ------------------------------------------------------------------

    def normalize(
        self,
        job: JobSpec,
        raw_items: list[RawItem],
        params: Optional[dict] = None,
    ) -> NormalizeResult:
        if job.name == "tce_rj_licitacoes":
            return self._normalize_licitacoes(raw_items)
        if job.name == "tce_rj_contratos":
            return self._normalize_contratos(raw_items)
        if job.name == "tce_rj_penalidades":
            return self._normalize_penalidades(raw_items)
        raise ValueError(f"Unknown TCE-RJ job: {job.name}")

    # -- licitacoes -------------------------------------------------------

    def _normalize_licitacoes(self, raw_items: list[RawItem]) -> NormalizeResult:
        entities: list[CanonicalEntity] = []
        events: list[CanonicalEvent] = []

        for item in raw_items:
            d = item.data
            participants: list[CanonicalEventParticipant] = []

            # Buyer (procuring entity / orgao)
            cnpj_orgao = _clean(d.get("cnpj_orgao"))
            nome_orgao = _clean(d.get("orgao")) or "Órgão não identificado"
            if cnpj_orgao:
                buyer = _cnpj_entity(cnpj_orgao, nome_orgao)
                entities.append(buyer)
                participants.append(
                    CanonicalEventParticipant(entity_ref=buyer, role="procuring_entity")
                )

            # Bidder (licitante), if present
            cnpj_licitante = _clean(d.get("cnpj_licitante"))
            nome_licitante = _clean(d.get("licitante")) or "Licitante não identificado"
            if cnpj_licitante:
                bidder = _cnpj_entity(cnpj_licitante, nome_licitante)
                entities.append(bidder)
                participants.append(
                    CanonicalEventParticipant(entity_ref=bidder, role="supplier")
                )

            # Value
            valor_raw = d.get("valorEstimado") or d.get("valor_estimado")
            valor: Optional[float] = None
            if valor_raw is not None:
                try:
                    valor = float(valor_raw)
                except (TypeError, ValueError):
                    pass

            event = CanonicalEvent(
                source_connector="tce_rj",
                source_id=item.raw_id,
                type="licitacao",
                description=_clean(d.get("objeto")),
                occurred_at=_parse_any_datetime(d.get("dataAbertura") or d.get("data_abertura")),
                value_brl=valor,
                attrs={
                    "modalidade": _clean(d.get("modalidade")),
                    "exercicio": _clean(d.get("exercicio")),
                    "municipio": _clean(d.get("municipio")),
                    "numero_licitacao": _clean(d.get("numero_licitacao") or d.get("numero")),
                },
                participants=participants,
            )
            events.append(event)

        return NormalizeResult(entities=entities, events=events)

    # -- contratos --------------------------------------------------------

    def _normalize_contratos(self, raw_items: list[RawItem]) -> NormalizeResult:
        entities: list[CanonicalEntity] = []
        events: list[CanonicalEvent] = []

        for item in raw_items:
            d = item.data
            participants: list[CanonicalEventParticipant] = []

            # Buyer (orgao)
            cnpj_orgao = _clean(d.get("cnpj_orgao"))
            nome_orgao = _clean(d.get("orgao")) or "Órgão não identificado"
            if cnpj_orgao:
                buyer = _cnpj_entity(cnpj_orgao, nome_orgao)
                entities.append(buyer)
                participants.append(
                    CanonicalEventParticipant(entity_ref=buyer, role="buyer")
                )

            # Supplier (fornecedor)
            cnpj_fornecedor = _clean(d.get("fornecedor_cnpj") or d.get("cnpj_fornecedor"))
            nome_fornecedor = _clean(d.get("fornecedor_nome") or d.get("fornecedor")) or "Fornecedor não identificado"
            if cnpj_fornecedor:
                supplier = _cnpj_entity(cnpj_fornecedor, nome_fornecedor)
                entities.append(supplier)
                participants.append(
                    CanonicalEventParticipant(entity_ref=supplier, role="supplier")
                )

            # Value
            valor: Optional[float] = None
            valor_raw = d.get("valor")
            if valor_raw is not None:
                try:
                    valor = float(valor_raw)
                except (TypeError, ValueError):
                    pass

            vigencia_inicio = _parse_any_datetime(d.get("vigencia_inicio"))
            vigencia_fim = _parse_any_datetime(d.get("vigencia_fim"))

            event = CanonicalEvent(
                source_connector="tce_rj",
                source_id=item.raw_id,
                type="contrato",
                description=_clean(d.get("objeto")),
                occurred_at=vigencia_inicio,
                value_brl=valor,
                attrs={
                    "vigencia_inicio": vigencia_inicio.isoformat() if vigencia_inicio else None,
                    "vigencia_fim": vigencia_fim.isoformat() if vigencia_fim else None,
                    "numero_contrato": _clean(d.get("numero_contrato") or d.get("numero")),
                    "municipio": _clean(d.get("municipio")),
                    "exercicio": _clean(d.get("exercicio")),
                },
                participants=participants,
            )
            events.append(event)

        return NormalizeResult(entities=entities, events=events)

    # -- penalidades ------------------------------------------------------

    def _normalize_penalidades(self, raw_items: list[RawItem]) -> NormalizeResult:
        entities: list[CanonicalEntity] = []
        events: list[CanonicalEvent] = []

        for item in raw_items:
            d = item.data
            participants: list[CanonicalEventParticipant] = []

            cpf_cnpj = _clean(d.get("cpf_cnpj") or d.get("cnpj") or d.get("cpf"))
            nome = _clean(d.get("nome")) or "Não identificado"

            if cpf_cnpj:
                if len(cpf_cnpj) == 14:
                    entity = CanonicalEntity(
                        source_connector="tce_rj",
                        source_id=cpf_cnpj,
                        type="company",
                        name=nome,
                        identifiers={"cnpj": cpf_cnpj},
                    )
                else:
                    entity = CanonicalEntity(
                        source_connector="tce_rj",
                        source_id=cpf_cnpj,
                        type="person",
                        name=nome,
                        identifiers={"cpf": cpf_cnpj},
                    )
                entities.append(entity)
                participants.append(
                    CanonicalEventParticipant(entity_ref=entity, role="sanctioned")
                )

            event = CanonicalEvent(
                source_connector="tce_rj",
                source_id=item.raw_id,
                type="penalidade_tce_rj",
                subtype=_clean(d.get("tipo_penalidade")),
                description=_clean(d.get("descricao") or d.get("objeto")),
                occurred_at=_parse_any_datetime(d.get("data_publicacao")),
                attrs={
                    "processo": _clean(d.get("processo")),
                    "tipo_penalidade": _clean(d.get("tipo_penalidade")),
                    "municipio": _clean(d.get("municipio")),
                },
                participants=participants,
            )
            events.append(event)

        return NormalizeResult(entities=entities, events=events)

    # ------------------------------------------------------------------
    # rate limit
    # ------------------------------------------------------------------

    def rate_limit_policy(self) -> RateLimitPolicy:
        return RateLimitPolicy(requests_per_second=5, burst=10)
