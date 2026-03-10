"""Connector for PNCP — Portal Nacional de Contratações Públicas.

API docs: https://pncp.gov.br/api/consulta/swagger-ui/index.html
Auth: Public consultation API (no auth needed for search endpoints).
Date format: YYYYMMDD (e.g. 20260101).

Pagination: PNCP caps at 10 pages per query. To cover large date ranges
we split into monthly windows and paginate within each window.
Cursor format: "w{window_idx}p{page}" (e.g. "w0p1", "w5p3").
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

from shared.connectors.base import BaseConnector, JobSpec, RateLimitPolicy
from shared.connectors.http_client import pncp_client, DEFAULT_PAGE_SIZE
from shared.models.canonical import (
    CanonicalEntity,
    CanonicalEvent,
    CanonicalEventParticipant,
    NormalizeResult,
)
from shared.models.raw import RawItem

# PNCP uses YYYYMMDD dates; most endpoints require dataInicial + dataFinal.
_DEFAULT_WINDOW_DAYS = 1825  # ~5 years
_MAX_PAGES_PER_WINDOW = 10  # PNCP hard limit
_PNCP_TIMEOUT = httpx.Timeout(connect=20.0, read=180.0, write=20.0, pool=20.0)
_PNCP_REDUCED_PAGE_SIZE = 100


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


def _resolve_window_bounds(params: Optional[dict]) -> tuple[datetime, datetime]:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=_DEFAULT_WINDOW_DAYS)
    if not params:
        return start, end

    raw_start = params.get("dataInicial")
    raw_end = params.get("dataFinal")
    if raw_start:
        start = _parse_yyyymmdd(raw_start)
    if raw_end:
        end = _parse_yyyymmdd(raw_end)
    if start > end:
        raise ValueError(f"Invalid PNCP date range: {start.date()} > {end.date()}")
    return start, end


def _parse_pncp_cursor(cursor: Optional[str]) -> tuple[int, int]:
    """Parse composite cursor 'w{window}p{page}' → (window_idx, page).

    Legacy numeric cursors (from before windowed pagination) are treated
    as a fresh start: (0, 1).
    """
    if not cursor:
        return 0, 1
    if cursor.startswith("w") and "p" in cursor:
        parts = cursor[1:].split("p", 1)
        return int(parts[0]), int(parts[1])
    # Legacy numeric cursor — restart with windowed pagination
    return 0, 1


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


class PNCPConnector(BaseConnector):
    """Connector for PNCP — Portal Nacional de Contratações Públicas."""

    @property
    def name(self) -> str:
        return "pncp"

    def list_jobs(self) -> list[JobSpec]:
        return [
            JobSpec(
                name="pncp_contracting_notices",
                description="Contracting notices (editais)",
                domain="licitacao",
                enabled=True,
            ),
            JobSpec(
                name="pncp_contracts",
                description="Contracts registered on PNCP",
                domain="contrato",
                enabled=True,
            ),
            JobSpec(
                name="pncp_arp",
                description="Atas de Registro de Preços",
                domain="licitacao",
                enabled=True,
            ),
        ]

    async def fetch(
        self,
        job: JobSpec,
        cursor: Optional[str] = None,
        params: Optional[dict] = None,
    ) -> tuple[list[RawItem], Optional[str]]:
        window_idx, page = _parse_pncp_cursor(cursor)
        start, end = _resolve_window_bounds(params)
        windows = _monthly_windows_between(start, end)

        if window_idx >= len(windows):
            return [], None

        di, df = windows[window_idx]

        # /contratacoes/publicacao requires codigoModalidadeContratacao and
        # only reliably works with smaller page sizes (<=20).
        if job.name == "pncp_contracting_notices":
            page_size = 20
        else:
            page_size = min(DEFAULT_PAGE_SIZE, 500)  # PNCP max is 500

        query_params: dict = {
            "pagina": page,
            "tamanhoPagina": page_size,
            "dataInicial": di,
            "dataFinal": df,
        }

        # /contratacoes/publicacao requires codigoModalidadeContratacao (mandatory).
        if job.name == "pncp_contracting_notices":
            query_params.setdefault("codigoModalidadeContratacao", 8)

        # Preserve caller-provided filters, but never override windowed dates/page.
        if params:
            mapped = dict(params)
            mapped.pop("dataInicial", None)
            mapped.pop("dataFinal", None)
            mapped.pop("pagina", None)
            mapped.pop("tamanhoPagina", None)
            query_params.update(mapped)

        endpoint = self._endpoint_for(job.name)

        try:
            async with pncp_client() as client:
                response = await client.get(endpoint, params=query_params, timeout=_PNCP_TIMEOUT)
                response.raise_for_status()
                if response.status_code == 204:
                    body = []
                else:
                    body = response.json()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 500:
                # PNCP 500s on specific windows are common (corrupted/unavailable data).
                # Skip this window rather than failing the entire task.
                from shared.logging import log as _log
                _log.warning(
                    "pncp.window_skip_500",
                    endpoint=endpoint,
                    window=f"{di}/{df}",
                    job=job.name,
                )
                if window_idx + 1 < len(windows):
                    return [], f"w{window_idx + 1}p1"
                return [], None
            raise
        except httpx.ReadTimeout:
            # Large pages occasionally time out on PNCP; retry once with a smaller page.
            if page_size <= _PNCP_REDUCED_PAGE_SIZE:
                raise
            page_size = _PNCP_REDUCED_PAGE_SIZE
            query_params["tamanhoPagina"] = page_size
            async with pncp_client() as client:
                response = await client.get(endpoint, params=query_params, timeout=_PNCP_TIMEOUT)
                response.raise_for_status()
                if response.status_code == 204:
                    body = []
                else:
                    body = response.json()

        records = body if isinstance(body, list) else body.get("data", body.get("registros", []))
        items = [
            RawItem(raw_id=f"{job.name}:w{window_idx}p{page}:{i}", data=r)
            for i, r in enumerate(records)
        ]

        # Determine next cursor
        if len(records) >= page_size and page < _MAX_PAGES_PER_WINDOW:
            next_cursor = f"w{window_idx}p{page + 1}"
        elif window_idx + 1 < len(windows):
            next_cursor = f"w{window_idx + 1}p1"
        else:
            next_cursor = None

        return items, next_cursor

    def _endpoint_for(self, job_name: str) -> str:
        mapping = {
            "pncp_contracting_notices": "/contratacoes/publicacao",
            "pncp_contracts": "/contratos",
            "pncp_arp": "/atas",
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
        entities: list[CanonicalEntity] = []
        events: list[CanonicalEvent] = []

        for item in raw_items:
            d = item.data
            # /contratacoes/publicacao nests orgao under "orgaoEntidade";
            # other endpoints use flat "cnpjOrgao"/"nomeOrgao".
            _orgao_ent = d.get("orgaoEntidade") or {}
            _unidade = d.get("unidadeOrgao") or {}
            _orgao_cnpj = (
                d.get("cnpjOrgao")
                or _orgao_ent.get("cnpj")
                or d.get("cnpj")
                or ""
            )
            _orgao_name = (
                d.get("nomeOrgao")
                or _orgao_ent.get("razaoSocial")
                or _unidade.get("nomeUnidade")
                or d.get("razaoSocial")
                or ""
            )
            orgao = CanonicalEntity(
                source_connector="pncp",
                source_id=_orgao_cnpj or item.raw_id,
                type="org",
                name=_orgao_name,
                identifiers={"cnpj": _orgao_cnpj},
            )
            entities.append(orgao)

            # Extract supplier/winner if present in raw data
            fornecedor_ni = d.get("niFornecedor", d.get("cnpjFornecedor", ""))
            fornecedor_nome = d.get(
                "nomeRazaoSocialFornecedor", d.get("nomeFornecedor", "")
            )

            if fornecedor_ni or fornecedor_nome:
                fornecedor = CanonicalEntity(
                    source_connector="pncp",
                    source_id=fornecedor_ni or f"{item.raw_id}:fornecedor",
                    type="company",
                    name=fornecedor_nome or fornecedor_ni,
                    identifiers=(
                        {"cnpj": fornecedor_ni} if fornecedor_ni else {}
                    ),
                )
                entities.append(fornecedor)
                # Licitações list bidders; contratos/ARPs list suppliers/winners.
                supplier_role = "bidder" if job.domain == "licitacao" else "supplier"
                participants = [
                    CanonicalEventParticipant(entity_ref=orgao, role="buyer"),
                    CanonicalEventParticipant(
                        entity_ref=orgao, role="procuring_entity"
                    ),
                    CanonicalEventParticipant(
                        entity_ref=fornecedor, role=supplier_role
                    ),
                ]
            else:
                participants = [
                    CanonicalEventParticipant(entity_ref=orgao, role="orgao"),
                    CanonicalEventParticipant(
                        entity_ref=orgao, role="procuring_entity"
                    ),
                    CanonicalEventParticipant(entity_ref=orgao, role="buyer"),
                ]

            events.append(
                CanonicalEvent(
                    source_connector="pncp",
                    source_id=item.raw_id,
                    type=job.domain,
                    subtype=d.get("modalidadeNome", ""),
                    description=d.get("objetoCompra", d.get("objeto", "")),
                    occurred_at=_parse_any_datetime(
                        d.get("dataPublicacaoPncp")
                        or d.get("dataAberturaProposta")
                        or d.get("dataAssinatura")
                    ),
                    value_brl=d.get("valorTotalEstimado", d.get("valorGlobal")),
                    attrs={
                        "modalidade": d.get("modalidadeNome", ""),
                        "modality": d.get("modalidadeNome", ""),
                        "situacao": d.get("situacaoCompra", d.get("situacao", "")),
                        "catmat_group": str(
                            d.get("codigoCatmat") or d.get("catmat_group") or "sem classificacao"
                        ),
                        "uf": (
                            (d.get("unidadeOrgao") or {}).get("ufSigla", "")
                            if isinstance(d.get("unidadeOrgao"), dict)
                            else d.get("uf", "")
                        ),
                    },
                    participants=participants,
                )
            )

        return NormalizeResult(entities=entities, events=events)

    def rate_limit_policy(self) -> RateLimitPolicy:
        return RateLimitPolicy(requests_per_second=10, burst=20)
