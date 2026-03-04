"""Connector for government contracts via Compras.gov.br open-data API.

Primary source: compras.dados.gov.br /contratos/v1/contratos.json
Fallback source: PNCP /api/consulta/v1/contratos (when primary times out/unavailable)

Fallback uses monthly-windowed pagination (cursor format: "w{idx}p{page}")
to stay under PNCP's 10-page limit per query.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

from shared.connectors.base import BaseConnector, JobSpec, RateLimitPolicy
from shared.logging import log
from shared.connectors.http_client import (
    DEFAULT_PAGE_SIZE,
    comprasnet_contratos_client,
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


class ComprasNetContratosConnector(BaseConnector):
    """Connector for government contracts (compras.dados.gov.br open-data)."""

    @property
    def name(self) -> str:
        return "comprasnet_contratos"

    def list_jobs(self) -> list[JobSpec]:
        return [
            JobSpec(
                name="cnet_contracts",
                description="Government contracts (open-data)",
                domain="contrato",
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
            return await self._fetch_pncp_windowed(job, cursor, params)

        offset = int(cursor) if cursor else 0
        query_params: dict = {"offset": offset, "limit": DEFAULT_PAGE_SIZE}
        if params:
            query_params.update(params)

        records: list[dict]
        page_size_for_next = DEFAULT_PAGE_SIZE
        try:
            async with comprasnet_contratos_client() as client:
                response = await client.get(
                    "/contratos/v1/contratos.json",
                    params=query_params,
                    timeout=_PRIMARY_TIMEOUT,
                )
                if response.status_code == 404:
                    log.warning(
                        "comprasnet_contratos.not_found",
                        endpoint="/contratos/v1/contratos.json",
                        status=404,
                    )
                    return [], None
                response.raise_for_status()
                records = _extract_records([] if response.status_code == 204 else response.json())
        except httpx.HTTPError:
            # Primary source down — switch to windowed PNCP fallback
            return await self._fetch_pncp_windowed(job, "w0p1", params)

        items = [
            RawItem(raw_id=f"{job.name}:{offset}:{i}", data=r)
            for i, r in enumerate(records)
        ]
        next_cursor = (
            str(offset + len(records))
            if len(records) >= page_size_for_next
            else None
        )
        return items, next_cursor

    async def _fetch_pncp_windowed(
        self,
        job: JobSpec,
        cursor: str,
        params: Optional[dict] = None,
    ) -> tuple[list[RawItem], Optional[str]]:
        """Fetch contracts from PNCP with monthly-windowed pagination."""
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
        }
        query.update(mapped)

        async with pncp_client() as client:
            resp = await client.get("/contratos", params=query)
            if resp.status_code == 404:
                log.warning(
                    "comprasnet_contratos.not_found",
                    endpoint="/contratos",
                    status=404,
                )
                return [], None
            resp.raise_for_status()
            rows = _extract_records([] if resp.status_code == 204 else resp.json())

        records = [_map_pncp_contract(row) for row in rows]
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
            doc = _digits_only(
                d.get("fornecedor_cnpj_cpf_idgener", d.get("cnpj_contratada", ""))
            )
            identifiers = (
                {"cnpj": doc}
                if len(doc) == 14
                else {"cpf": doc} if len(doc) == 11 else {}
            )

            contract_start = _parse_any_datetime(
                d.get("vigencia_inicio")
                or d.get("data_assinatura")
                or d.get("data_inicio_vigencia")
            )
            contract_end = _parse_any_datetime(
                d.get("vigencia_fim") or d.get("data_fim_vigencia")
            )

            fornecedor = CanonicalEntity(
                source_connector="comprasnet_contratos",
                source_id=doc or d.get("cnpj_contratada", item.raw_id),
                type="person" if len(doc) == 11 else "company",
                name=d.get("fornecedor_nome", d.get("nome_contratada", "")),
                identifiers=identifiers,
            )
            entities.append(fornecedor)

            orgao_nome = d.get("orgao_nome", "")
            uasg = str(d.get("unidade_codigo", "")).strip()
            buyer_identifiers = {"uasg": uasg} if uasg else {}
            buyer = CanonicalEntity(
                source_connector="comprasnet_contratos",
                source_id=uasg or orgao_nome or f"{item.raw_id}:buyer",
                type="org",
                name=orgao_nome or "Órgão contratante",
                identifiers=buyer_identifiers,
            )
            entities.append(buyer)

            original_value = _safe_float(
                d.get("valor_global", d.get("valor_inicial"))
            )

            events.append(
                CanonicalEvent(
                    source_connector="comprasnet_contratos",
                    source_id=item.raw_id,
                    type="contrato",
                    description=d.get("objeto", ""),
                    occurred_at=contract_start,
                    value_brl=original_value,
                    attrs={
                        "numero": d.get("numero", ""),
                        "situacao": d.get("categoria", ""),
                        "vigencia_inicio": d.get("vigencia_inicio", d.get("data_assinatura", "")),
                        "vigencia_fim": d.get("vigencia_fim", ""),
                        "contract_start": contract_start.isoformat() if contract_start else None,
                        "contract_end": contract_end.isoformat() if contract_end else None,
                        "orgao": d.get("orgao_nome", ""),
                        "uasg": d.get("unidade_codigo", ""),
                        "original_value": original_value,
                        "amendment_count": d.get("qtd_aditivos", d.get("amendment_count", 0)),
                        "amendments_total_value": _safe_float(
                            d.get("valor_total_aditivos", d.get("amendments_total_value"))
                        )
                        or 0.0,
                    },
                    participants=[
                        CanonicalEventParticipant(entity_ref=fornecedor, role="supplier"),
                        CanonicalEventParticipant(entity_ref=buyer, role="buyer"),
                        CanonicalEventParticipant(entity_ref=buyer, role="procuring_entity"),
                    ],
                )
            )

        return NormalizeResult(entities=entities, events=events)

    def rate_limit_policy(self) -> RateLimitPolicy:
        return RateLimitPolicy(requests_per_second=5, burst=10)


def _digits_only(value: object) -> str:
    if value is None:
        return ""
    return "".join(ch for ch in str(value) if ch.isdigit())


def _safe_float(value: object) -> Optional[float]:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    normalized = raw
    if "," in raw and "." in raw:
        normalized = raw.replace(".", "").replace(",", ".")
    elif "," in raw:
        normalized = raw.replace(",", ".")
    try:
        return float(normalized)
    except (TypeError, ValueError):
        return None


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


def _map_pncp_contract(row: dict) -> dict:
    categoria = row.get("categoriaProcesso", {})
    orgao = row.get("orgaoEntidade", {})
    unidade = row.get("unidadeOrgao", {})
    return {
        "fornecedor_cnpj_cpf_idgener": row.get("niFornecedor", ""),
        "fornecedor_nome": row.get("nomeRazaoSocialFornecedor", ""),
        "objeto": row.get("objetoContrato", ""),
        "valor_global": row.get("valorGlobal", row.get("valorInicial")),
        "numero": row.get("numeroContratoEmpenho", row.get("numeroControlePNCP", "")),
        "categoria": categoria.get("nome", categoria.get("descricao", "")),
        "data_assinatura": row.get("dataAssinatura"),
        "data_inicio_vigencia": row.get("dataVigenciaInicio"),
        "data_fim_vigencia": row.get("dataVigenciaFim"),
        "orgao_nome": orgao.get("razaoSocial", ""),
        "unidade_codigo": unidade.get("codigoUnidade", ""),
        "source_fallback": "pncp",
        "source_pncp_id": row.get("numeroControlePNCP") or row.get("numeroControlePncpCompra"),
    }
