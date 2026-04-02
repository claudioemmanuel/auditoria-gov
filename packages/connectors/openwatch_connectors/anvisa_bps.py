"""Connector for ANVISA/BPS (Banco de Preços em Saúde)."""

from datetime import datetime, timezone
from typing import Optional

import httpx

from openwatch_connectors.base import (
    BaseConnector,
    JobSpec,
    RateLimitPolicy,
    SourceClassification,
)
from openwatch_connectors.http_client import anvisa_bps_client, anvisa_bulario_client
from shared.logging import log
from openwatch_models.canonical import (
    CanonicalEntity,
    CanonicalEvent,
    CanonicalEventParticipant,
    NormalizeResult,
)
from openwatch_models.raw import RawItem

_BPS_DEFAULT_PAGE_SIZE = 200
_BULARIO_DEFAULT_PAGE = 0


def _digits_only(value: object) -> str:
    if value is None:
        return ""
    return "".join(ch for ch in str(value) if ch.isdigit())


def _is_valid_cnpj(value: object) -> bool:
    cnpj = _digits_only(value)
    if len(cnpj) != 14:
        return False
    if cnpj == cnpj[0] * 14:
        return False

    def _calc_digit(base: str, weights: list[int]) -> int:
        total = sum(int(d) * w for d, w in zip(base, weights))
        mod = total % 11
        return 0 if mod < 2 else 11 - mod

    first_digit = _calc_digit(cnpj[:12], [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    second_digit = _calc_digit(cnpj[:13], [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    return cnpj[-2:] == f"{first_digit}{second_digit}"


def _extract_valid_cnpj(record: dict, keys: tuple[str, ...]) -> str:
    for key in keys:
        if key not in record:
            continue
        candidate = _digits_only(record.get(key))
        if _is_valid_cnpj(candidate):
            return candidate
    return ""


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
    except (ValueError, TypeError):
        return None


def _as_bool(value: object) -> Optional[bool]:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    raw = str(value).strip().lower()
    if raw in {"1", "true", "t", "sim", "s", "y", "yes"}:
        return True
    if raw in {"0", "false", "f", "nao", "não", "n", "no"}:
        return False
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
        "%d/%m/%Y %H:%M:%S",
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


def _next_bps_cursor(offset: int, page_size: int, returned_count: int) -> Optional[str]:
    if returned_count < page_size:
        return None
    return str(offset + page_size)


def _extract_bulario_rows(payload: object) -> list[dict]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if not isinstance(payload, dict):
        return []

    for key in ("content", "items", "results", "data", "bulario", "medicamentos"):
        rows = payload.get(key)
        if isinstance(rows, list):
            return [row for row in rows if isinstance(row, dict)]
    return []


def _coerce_int(value: object) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(str(value))
    except (ValueError, TypeError):
        return None


def _next_bulario_cursor(payload: object, current_page: int) -> Optional[str]:
    if not isinstance(payload, dict):
        return None

    next_page = _coerce_int(payload.get("next") or payload.get("proximaPagina"))
    if next_page is not None:
        return str(next_page)

    pagination = payload.get("pagination") or payload.get("page")
    if isinstance(pagination, dict):
        page_num = _coerce_int(
            pagination.get("number")
            or pagination.get("page")
            or pagination.get("currentPage")
        )
        total_pages = _coerce_int(
            pagination.get("totalPages")
            or pagination.get("total_pages")
            or pagination.get("pages")
        )
        if total_pages is not None:
            current = current_page if page_num is None else page_num
            if current + 1 < total_pages:
                return str(current + 1)
        has_next = pagination.get("hasNext") or pagination.get("has_next")
        if has_next is True:
            current = current_page if page_num is None else page_num
            return str(current + 1)

    total_pages = _coerce_int(
        payload.get("totalPages") or payload.get("total_pages") or payload.get("pages")
    )
    page_num = _coerce_int(payload.get("number") or payload.get("page") or payload.get("pagina"))
    if total_pages is not None:
        current = current_page if page_num is None else page_num
        if current + 1 < total_pages:
            return str(current + 1)

    return None


class AnvisaBPSConnector(BaseConnector):
    @property
    def name(self) -> str:
        return "anvisa_bps"

    @property
    def classification(self) -> SourceClassification:
        return SourceClassification.ENRICHMENT_ONLY

    def list_jobs(self) -> list[JobSpec]:
        return [
            JobSpec(
                name="anvisa_bps_prices",
                description="BPS medicine procurement prices",
                domain="health_procurement",
                supports_incremental=True,
                enabled=True,
                default_params={"limit": _BPS_DEFAULT_PAGE_SIZE},
            ),
            JobSpec(
                name="anvisa_bulario_registry",
                description="ANVISA bulario registry lookup",
                domain="regulatory_record",
                supports_incremental=True,
                enabled=True,
                default_params={},
            ),
        ]

    async def fetch(
        self,
        job: JobSpec,
        cursor: Optional[str] = None,
        params: Optional[dict] = None,
    ) -> tuple[list[RawItem], Optional[str]]:
        if job.name == "anvisa_bps_prices":
            return await self._fetch_bps_prices(cursor, params)
        if job.name == "anvisa_bulario_registry":
            return await self._fetch_bulario(cursor, params)
        raise ValueError(f"Unknown ANVISA/BPS job: {job.name}")

    async def _fetch_bps_prices(
        self,
        cursor: Optional[str],
        params: Optional[dict],
    ) -> tuple[list[RawItem], Optional[str]]:
        page_size = _BPS_DEFAULT_PAGE_SIZE
        if params:
            configured_limit = _coerce_int(params.get("limit"))
            if configured_limit and configured_limit > 0:
                page_size = configured_limit

        offset = _coerce_int(cursor) if cursor else 0
        if offset is None or offset < 0:
            offset = 0

        try:
            async with anvisa_bps_client() as client:
                response = await client.get(
                    "/economia-da-saude/bps",
                    params={"limit": page_size, "offset": offset},
                )
                response.raise_for_status()
                payload: object = response.json()
        except httpx.HTTPError as exc:
            log.warning("anvisa_bps.fetch_error", job="anvisa_bps_prices", error=str(exc))
            return [], None

        rows: list[dict]
        if isinstance(payload, dict):
            bps_rows = payload.get("bps", [])
            rows = [row for row in bps_rows if isinstance(row, dict)] if isinstance(bps_rows, list) else []
        else:
            rows = []

        items = [
            RawItem(raw_id=f"anvisa_bps_prices:{offset + i}", data=row)
            for i, row in enumerate(rows)
        ]
        return items, _next_bps_cursor(offset=offset, page_size=page_size, returned_count=len(rows))

    async def _fetch_bulario(
        self,
        cursor: Optional[str],
        params: Optional[dict],
    ) -> tuple[list[RawItem], Optional[str]]:
        query: dict[str, object] = {}
        if params:
            nome = params.get("nome")
            principio_ativo = params.get("principio_ativo")
            if nome:
                query["nome"] = str(nome)
            if principio_ativo:
                query["principio_ativo"] = str(principio_ativo)

        page = _coerce_int(cursor) if cursor else _BULARIO_DEFAULT_PAGE
        if page is None or page < 0:
            page = _BULARIO_DEFAULT_PAGE
        if page > 0:
            query["page"] = page

        try:
            async with anvisa_bulario_client() as client:
                response = await client.get("/api/consulta/bulario", params=query)
                response.raise_for_status()
                payload: object = response.json()
        except httpx.HTTPError as exc:
            log.warning("anvisa_bps.fetch_error", job="anvisa_bulario_registry", error=str(exc))
            return [], None

        rows = _extract_bulario_rows(payload)
        items = [
            RawItem(
                raw_id=(
                    f"anvisa_bulario_registry:{row.get('numero_processo') or row.get('numeroProcesso') or i}"
                ),
                data=row,
            )
            for i, row in enumerate(rows)
        ]
        return items, _next_bulario_cursor(payload, current_page=page)

    def normalize(
        self,
        job: JobSpec,
        raw_items: list[RawItem],
        params: Optional[dict] = None,
    ) -> NormalizeResult:
        if job.name == "anvisa_bps_prices":
            return self._normalize_bps(raw_items)
        if job.name == "anvisa_bulario_registry":
            return self._normalize_bulario(raw_items)
        raise ValueError(f"Unknown ANVISA/BPS job: {job.name}")

    def _normalize_bps(self, raw_items: list[RawItem]) -> NormalizeResult:
        entities: list[CanonicalEntity] = []
        events: list[CanonicalEvent] = []

        for item in raw_items:
            d = item.data
            participants: list[CanonicalEventParticipant] = []

            supplier_cnpj = _extract_valid_cnpj(
                d,
                (
                    "cnpj_do_fornecedor",
                    "cnpj_fornecedor",
                    "cnpjFornecedor",
                    "cnpj",
                ),
            )
            supplier_name = (
                str(
                    d.get("nome_do_fornecedor")
                    or d.get("fornecedor")
                    or d.get("razao_social_fornecedor")
                    or "Fornecedor não identificado"
                )
            ).strip()
            if supplier_cnpj:
                supplier = CanonicalEntity(
                    source_connector="anvisa_bps",
                    source_id=f"cnpj:{supplier_cnpj}",
                    type="company",
                    name=supplier_name,
                    identifiers={"cnpj": supplier_cnpj},
                )
                entities.append(supplier)
                participants.append(CanonicalEventParticipant(entity_ref=supplier, role="supplier"))

            institution_cnpj = _extract_valid_cnpj(
                d,
                (
                    "cnpj_instituicao",
                    "cnpj_da_instituicao",
                    "cnpj_estabelecimento",
                    "cnpj_orgao",
                ),
            )
            institution_name = (
                str(
                    d.get("nome_instituicao")
                    or d.get("instituicao")
                    or d.get("nome_estabelecimento")
                    or "Instituição não identificada"
                )
            ).strip()
            if institution_cnpj:
                institution = CanonicalEntity(
                    source_connector="anvisa_bps",
                    source_id=f"org:{institution_cnpj}",
                    type="org",
                    name=institution_name,
                    identifiers={"cnpj": institution_cnpj},
                )
                entities.append(institution)
                participants.append(CanonicalEventParticipant(entity_ref=institution, role="buyer"))

            quantity = _safe_float(d.get("quantidade") or d.get("quantidade_comprada"))
            unit_price = _safe_float(d.get("preco_unitario") or d.get("valor_unitario"))
            total_price = _safe_float(d.get("preco_total"))
            value_brl = total_price
            if value_brl is None and quantity is not None and unit_price is not None:
                value_brl = quantity * unit_price

            event = CanonicalEvent(
                source_connector="anvisa_bps",
                source_id=item.raw_id,
                type="health_procurement",
                subtype="medicine_purchase",
                description=str(d.get("descricao_catmat") or d.get("descricao") or "").strip() or None,
                occurred_at=_parse_any_datetime(
                    d.get("data_compra")
                    or d.get("data")
                    or d.get("data_da_compra")
                ),
                value_brl=value_brl,
                attrs={
                    "catmat": d.get("catmat") or d.get("codigo_catmat"),
                    "code_br": d.get("code_br") or d.get("codigo_br"),
                    "descricao_catmat": d.get("descricao_catmat"),
                    "modalidade": d.get("modalidade"),
                    "tipo_compra": d.get("tipo_compra"),
                    "uf": d.get("uf"),
                    "municipio": d.get("municipio"),
                    "generico": _as_bool(
                        d.get("generico")
                        or d.get("medicamento_generico")
                        or d.get("eh_generico")
                    ),
                    "quantidade": quantity,
                    "preco_unitario": unit_price,
                    "preco_total": total_price,
                },
                participants=participants,
            )
            events.append(event)

        return NormalizeResult(entities=entities, events=events)

    def _normalize_bulario(self, raw_items: list[RawItem]) -> NormalizeResult:
        entities: list[CanonicalEntity] = []
        events: list[CanonicalEvent] = []

        for item in raw_items:
            d = item.data
            participants: list[CanonicalEventParticipant] = []

            manufacturer_cnpj = _extract_valid_cnpj(
                d,
                (
                    "cnpj_fabricante",
                    "cnpjFabricante",
                    "cnpj_empresa",
                    "cnpjEmpresa",
                ),
            )
            manufacturer_name = (
                str(
                    d.get("nome_empresa")
                    or d.get("empresa")
                    or d.get("fabricante")
                    or "Fabricante não identificado"
                )
            ).strip()
            if manufacturer_cnpj:
                manufacturer = CanonicalEntity(
                    source_connector="anvisa_bps",
                    source_id=f"cnpj:{manufacturer_cnpj}",
                    type="company",
                    name=manufacturer_name,
                    identifiers={"cnpj": manufacturer_cnpj},
                )
                entities.append(manufacturer)
                participants.append(
                    CanonicalEventParticipant(entity_ref=manufacturer, role="manufacturer")
                )

            event = CanonicalEvent(
                source_connector="anvisa_bps",
                source_id=item.raw_id,
                type="regulatory_record",
                subtype="anvisa_drug_registration",
                description=str(
                    d.get("nome_produto")
                    or d.get("nomeMedicamento")
                    or d.get("nome")
                    or ""
                ).strip() or None,
                occurred_at=_parse_any_datetime(
                    d.get("data_publicacao")
                    or d.get("dataPublicacao")
                    or d.get("data_registro")
                ),
                attrs={
                    "numero_registro": d.get("numero_registro") or d.get("numeroRegistro"),
                    "principio_ativo": d.get("principio_ativo") or d.get("principioAtivo"),
                    "categoria_regulatoria": (
                        d.get("categoria_regulatoria") or d.get("categoriaRegulatoria")
                    ),
                    "data_vencimento_registro": (
                        d.get("data_vencimento_registro")
                        or d.get("dataVencimentoRegistro")
                    ),
                    "numero_processo": d.get("numero_processo") or d.get("numeroProcesso"),
                },
                participants=participants,
            )
            events.append(event)

        return NormalizeResult(entities=entities, events=events)

    def rate_limit_policy(self) -> RateLimitPolicy:
        return RateLimitPolicy(requests_per_second=1, burst=1)
