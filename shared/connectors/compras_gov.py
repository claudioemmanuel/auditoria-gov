"""Connector for Compras.gov.br (compras.dados.gov.br).

API docs: https://compras.dados.gov.br/docs/home.html
Auth: None (public open-data API).
URL pattern: https://compras.dados.gov.br/{module}/v1/{resource}.json
Pagination: offset-based (not page-based).

Fallback: When the primary source fails, licitações are fetched from PNCP
using monthly-windowed pagination (cursor format: "w{idx}p{page}").
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

from shared.connectors.base import BaseConnector, JobSpec, RateLimitPolicy
from shared.connectors.http_client import (
    DEFAULT_PAGE_SIZE,
    compras_gov_client,
    pncp_client,
)
from shared.models.canonical import (
    CanonicalEntity,
    CanonicalEvent,
    CanonicalEventParticipant,
    NormalizeResult,
)
from shared.models.raw import RawItem

_PRIMARY_TIMEOUT = httpx.Timeout(connect=20.0, read=120.0, write=20.0, pool=20.0)
_PNCP_FALLBACK_PAGE_SIZE = 10
_PNCP_FALLBACK_WINDOW_DAYS = 1825  # ~5 years
_PNCP_DEFAULT_MODALIDADE = 8
_MAX_PAGES_PER_WINDOW = 10  # PNCP hard limit


def _monthly_windows_between(start: datetime, end: datetime) -> list[tuple[str, str]]:
    """Split a [start, end] range into monthly windows (YYYYMMDD pairs)."""
    if start > end:
        return []
    windows: list[tuple[str, str]] = []
    current = start
    while current <= end:
        next_month = (current.replace(day=1) + timedelta(days=32)).replace(day=1)
        window_end = min(next_month - timedelta(days=1), end)
        windows.append((current.strftime("%Y%m%d"), window_end.strftime("%Y%m%d")))
        current = next_month
    return windows


def _parse_yyyymmdd(value: object) -> datetime:
    return datetime.strptime(str(value).strip(), "%Y%m%d").replace(tzinfo=timezone.utc)


def _parse_pncp_cursor(cursor: str) -> tuple[int, int]:
    """Parse 'w{window}p{page}' → (window_idx, page)."""
    if cursor.startswith("w") and "p" in cursor:
        parts = cursor[1:].split("p", 1)
        return int(parts[0]), int(parts[1])
    return 0, 1


class ComprasGovConnector(BaseConnector):
    """Connector for Compras.gov.br (compras.dados.gov.br)."""

    @property
    def name(self) -> str:
        return "compras_gov"

    def list_jobs(self) -> list[JobSpec]:
        return [
            JobSpec(
                name="compras_licitacoes_by_period",
                description="Procurement notices by period",
                domain="licitacao",
                enabled=True,
            ),
            JobSpec(
                name="compras_catalogo_catmat_full",
                description="CATMAT material catalog (full dump)",
                domain="catalogo",
                supports_incremental=False,
                enabled=True,
            ),
            JobSpec(
                name="compras_catalogo_catser_full",
                description="CATSER service catalog (full dump)",
                domain="catalogo",
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
        # Detect windowed PNCP fallback cursor from a previous page
        if cursor and cursor.startswith("w"):
            if job.name != "compras_licitacoes_by_period":
                raise ValueError(f"Windowed cursor not supported for job: {job.name}")
            return await self._fetch_pncp_windowed(job, cursor, params)

        offset = int(cursor) if cursor else 0
        query_params: dict = {"offset": offset, "limit": DEFAULT_PAGE_SIZE}

        if params:
            query_params.update(params)

        endpoint = self._endpoint_for(job.name)

        page_size_for_next = DEFAULT_PAGE_SIZE
        try:
            async with compras_gov_client() as client:
                response = await client.get(
                    endpoint,
                    params=query_params,
                    timeout=_PRIMARY_TIMEOUT,
                )
                response.raise_for_status()
                records = _extract_records(response.json())
        except httpx.HTTPError:
            if job.name != "compras_licitacoes_by_period":
                raise
            # Primary source down — switch to windowed PNCP fallback
            return await self._fetch_pncp_windowed(job, "w0p1", params)

        items = [
            RawItem(raw_id=f"{job.name}:{offset}:{i}", data=r)
            for i, r in enumerate(records)
        ]
        next_cursor = str(offset + len(records)) if len(records) >= page_size_for_next else None
        return items, next_cursor

    async def _fetch_pncp_windowed(
        self,
        job: JobSpec,
        cursor: str,
        params: Optional[dict] = None,
    ) -> tuple[list[RawItem], Optional[str]]:
        """Fetch licitações from PNCP with monthly-windowed pagination."""
        window_idx, page = _parse_pncp_cursor(cursor)

        mapped = dict(params or {})
        year = mapped.pop("ano", None)
        raw_start = mapped.pop("dataInicial", None)
        raw_end = mapped.pop("dataFinal", None)
        if year and not raw_start and not raw_end:
            raw_start = f"{int(year):04d}0101"
            raw_end = f"{int(year):04d}1231"

        end = datetime.now(timezone.utc)
        start = end - timedelta(days=_PNCP_FALLBACK_WINDOW_DAYS)
        if raw_start:
            start = _parse_yyyymmdd(raw_start)
        if raw_end:
            end = _parse_yyyymmdd(raw_end)
        if start > end:
            raise ValueError(f"Invalid PNCP fallback date range: {start.date()} > {end.date()}")

        windows = _monthly_windows_between(start, end)

        if window_idx >= len(windows):
            return [], None

        di, df = windows[window_idx]
        query: dict = {
            "pagina": page,
            "tamanhoPagina": _PNCP_FALLBACK_PAGE_SIZE,
            "dataInicial": di,
            "dataFinal": df,
            "codigoModalidadeContratacao": _PNCP_DEFAULT_MODALIDADE,
        }
        modalidade = mapped.pop("codigoModalidadeContratacao", None)
        if modalidade is not None:
            query["codigoModalidadeContratacao"] = int(modalidade)
        query.update(mapped)

        async with pncp_client() as client:
            response = await client.get("/contratacoes/publicacao", params=query)
            response.raise_for_status()
            rows = _extract_records(response.json())

        records = [_map_pncp_notice_to_compras(row) for row in rows]
        items = [
            RawItem(raw_id=f"{job.name}:w{window_idx}p{page}:{i}", data=r)
            for i, r in enumerate(records)
        ]

        if len(records) >= _PNCP_FALLBACK_PAGE_SIZE and page < _MAX_PAGES_PER_WINDOW:
            next_cursor = f"w{window_idx}p{page + 1}"
        elif window_idx + 1 < len(windows):
            next_cursor = f"w{window_idx + 1}p1"
        else:
            next_cursor = None

        return items, next_cursor

    def _endpoint_for(self, job_name: str) -> str:
        mapping = {
            "compras_licitacoes_by_period": "/licitacoes/v1/licitacoes.json",
            "compras_catalogo_catmat_full": "/materiais/v1/materiais.json",
            "compras_catalogo_catser_full": "/servicos/v1/servicos.json",
        }
        ep = mapping.get(job_name)
        if not ep:
            raise ValueError(f"Unknown job: {job_name}")
        return ep

    def normalize(
        self,
        job: JobSpec,
        raw_items: list[RawItem],
        params: Optional[dict] = None,
    ) -> NormalizeResult:
        if job.name == "compras_licitacoes_by_period":
            return self._normalize_licitacoes(raw_items)
        # Generic: wrap raw data in events
        events = [
            CanonicalEvent(
                source_connector="compras_gov",
                source_id=item.raw_id,
                type=job.domain,
                attrs=item.data,
            )
            for item in raw_items
        ]
        return NormalizeResult(events=events)

    def _normalize_licitacoes(self, items: list[RawItem]) -> NormalizeResult:
        entities: list[CanonicalEntity] = []
        events: list[CanonicalEvent] = []

        for item in items:
            d = item.data
            org_source_id = str(d.get("uasg", item.raw_id))
            org = CanonicalEntity(
                source_connector="compras_gov",
                source_id=org_source_id,
                type="org",
                name=d.get("nomeUasg", d.get("orgao", "")),
                identifiers={"uasg": str(d.get("uasg", ""))},
            )
            entities.append(org)

            participants = [
                CanonicalEventParticipant(entity_ref=org, role="procuring_entity"),
                CanonicalEventParticipant(entity_ref=org, role="buyer"),
            ]

            winner_entity = _build_company_entity(
                source_connector="compras_gov",
                payload=(
                    d.get("vencedor")
                    or d.get("fornecedorVencedor")
                    or d.get("fornecedor_vencedor")
                ),
                fallback_source_id=f"{item.raw_id}:winner",
            )
            if winner_entity:
                entities.append(winner_entity)
                participants.append(
                    CanonicalEventParticipant(entity_ref=winner_entity, role="winner")
                )
                participants.append(
                    CanonicalEventParticipant(entity_ref=winner_entity, role="bidder")
                )

            bidder_payloads = d.get("participantes") or d.get("propostas") or []
            if isinstance(bidder_payloads, list):
                seen_bidder_ids: set[str] = set()
                for i, bidder_payload in enumerate(bidder_payloads):
                    bidder_entity = _build_company_entity(
                        source_connector="compras_gov",
                        payload=bidder_payload,
                        fallback_source_id=f"{item.raw_id}:bidder:{i}",
                    )
                    if bidder_entity is None:
                        continue
                    if bidder_entity.source_id in seen_bidder_ids:
                        continue
                    seen_bidder_ids.add(bidder_entity.source_id)
                    entities.append(bidder_entity)
                    participants.append(
                        CanonicalEventParticipant(entity_ref=bidder_entity, role="bidder")
                    )

            occurred_at = _parse_licitacao_datetime(d)
            modality = d.get("modalidade", "")
            catmat_group = _normalize_catmat_group(
                d.get("catmat_group")
                or d.get("catmatGrupo")
                or d.get("catmat_code")
                or d.get("catmatCodigo")
            )
            events.append(
                CanonicalEvent(
                    source_connector="compras_gov",
                    source_id=item.raw_id,
                    type="licitacao",
                    subtype=modality,
                    description=d.get("objeto", ""),
                    occurred_at=occurred_at,
                    value_brl=d.get("valorEstimado"),
                    attrs={
                        "numero": d.get("numero", ""),
                        "situacao": d.get("situacao", ""),
                        "modality": modality,
                        "catmat_group": catmat_group,
                        "source_pncp_id": d.get("source_pncp_id", ""),
                        "uf": (
                            d.get("uf", "")
                            or d.get("siglaUf", "")
                            or d.get("ufOrgao", "")
                        ),
                    },
                    participants=participants,
                )
            )

        return NormalizeResult(entities=entities, events=events)

    def rate_limit_policy(self) -> RateLimitPolicy:
        return RateLimitPolicy(requests_per_second=10, burst=20)


def _extract_records(body: object) -> list[dict]:
    if isinstance(body, list):
        return [item for item in body if isinstance(item, dict)]
    if isinstance(body, dict):
        records = body.get("_embedded", {}).get("registros", [])
        if not records:
            records = body.get("registros", [])
        if not records:
            records = body.get("data", [])
        return [item for item in records if isinstance(item, dict)]
    return []


def _normalize_catmat_group(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return "nao_informado"
    if text.lower() in {
        "unknown",
        "sem classificacao",
        "sem classificação",
        "null",
        "none",
    }:
        return "nao_informado"
    return text


def _digits_only(value: object) -> str:
    if value is None:
        return ""
    return "".join(ch for ch in str(value) if ch.isdigit())


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
        "%Y%m%d",
        "%d/%m/%Y",
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


def _infer_year_from_source_pncp_id(value: object) -> Optional[datetime]:
    raw = str(value or "").strip()
    if not raw:
        return None
    year_candidate = raw.rsplit("/", 1)[-1]
    if len(year_candidate) == 4 and year_candidate.isdigit():
        year = int(year_candidate)
        if 1900 <= year <= 2100:
            return datetime(year, 1, 1, tzinfo=timezone.utc)
    return None


def _parse_licitacao_datetime(payload: dict) -> Optional[datetime]:
    candidates = [
        payload.get("dataPublicacaoPncp"),
        payload.get("dataPublicacao"),
        payload.get("dataAbertura"),
        payload.get("dataEncerramentoProposta"),
        payload.get("dataResultado"),
    ]
    for candidate in candidates:
        parsed = _parse_any_datetime(candidate)
        if parsed:
            return parsed
    return _infer_year_from_source_pncp_id(payload.get("source_pncp_id"))


def _build_company_entity(
    source_connector: str,
    payload: object,
    fallback_source_id: str,
) -> Optional[CanonicalEntity]:
    if not isinstance(payload, dict):
        return None

    name = (
        payload.get("nome")
        or payload.get("razaoSocial")
        or payload.get("fornecedor")
        or ""
    )
    raw_doc = (
        payload.get("cnpj")
        or payload.get("cpf")
        or payload.get("cnpjCpf")
        or payload.get("niFornecedor")
    )
    doc = _digits_only(raw_doc)
    identifiers: dict = {}
    if len(doc) == 14:
        identifiers["cnpj"] = doc
    elif len(doc) == 11:
        identifiers["cpf"] = doc

    if not name and not identifiers:
        return None

    source_id = doc or fallback_source_id
    entity_type = "company" if len(doc) != 11 else "person"
    return CanonicalEntity(
        source_connector=source_connector,
        source_id=source_id,
        type=entity_type,
        name=name or source_id,
        identifiers=identifiers,
    )


def _map_pncp_notice_to_compras(row: dict) -> dict:
    unidade = row.get("unidadeOrgao", {})
    orgao = row.get("orgaoEntidade", {})
    vencedor = row.get("fornecedor")
    participantes = row.get("participantes", [])
    return {
        "uasg": unidade.get("codigoUnidade", ""),
        "nomeUasg": unidade.get("nomeUnidade", ""),
        "orgao": orgao.get("razaoSocial", ""),
        "modalidade": row.get("modalidadeNome", ""),
        "objeto": row.get("objetoCompra", ""),
        "valorEstimado": row.get("valorTotalEstimado"),
        "numero": row.get("numeroCompra", row.get("numeroControlePNCP", "")),
        "situacao": row.get("situacaoCompra", ""),
        "dataPublicacaoPncp": row.get("dataPublicacaoPncp"),
        "dataAbertura": row.get("dataAberturaProposta"),
        "vencedor": vencedor if isinstance(vencedor, dict) else None,
        "participantes": participantes if isinstance(participantes, list) else [],
        "source_fallback": "pncp",
        "source_pncp_id": row.get("numeroControlePNCP"),
        "uf": unidade.get("ufSigla", ""),
    }
