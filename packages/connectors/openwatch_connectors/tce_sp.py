"""Connector for TCE-SP — Tribunal de Contas do Estado de São Paulo.

Covers:
  - Despesas: monthly municipal expenses (empenhos, liquidações, pagamentos).
  - Receitas: monthly municipal revenues.

Pagination:
  TCE-SP returns full month data per request (no intra-endpoint pagination).
  We iterate over municipalities × years × months using a composite cursor:
    "m{muni_idx}y{year}m{month}"
  Default: current year, months 1–12, for all 645 SP municipalities.
"""

import re
from datetime import datetime, timezone
from typing import Optional

from openwatch_connectors.base import BaseConnector, JobSpec, RateLimitPolicy
from openwatch_connectors.http_client import tce_sp_client
from openwatch_utils.logging import log
from openwatch_models.canonical import (
    CanonicalEntity,
    CanonicalEvent,
    CanonicalEventParticipant,
    NormalizeResult,
)
from openwatch_models.raw import RawItem

# São Paulo municipality codes used by the TCE-SP API.
# Loaded lazily from /municipios on first fetch; cached for the session.
_sp_municipios_cache: list[str] | None = None

_CURSOR_RE = re.compile(r"^m(\d+)y(\d{4})m(\d{1,2})$")

_DEFAULT_YEAR = datetime.now(tz=timezone.utc).year
_MONTHS = list(range(1, 13))


# ── Helpers ─────────────────────────────────────────────────────────────────


def _parse_brl_string(value: object) -> Optional[float]:
    """Parse Brazilian number format '1.234,56' -> 1234.56."""
    if value is None:
        return None
    raw = str(value).strip()
    if not raw or raw == "-":
        return None
    cleaned = raw.replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_cursor(cursor: Optional[str]) -> tuple[int, int, int]:
    """Parse composite cursor into (muni_idx, year, month).

    Returns (0, default_year, 1) when cursor is None (start of ingestion).
    """
    if cursor is None:
        return 0, _DEFAULT_YEAR, 1
    m = _CURSOR_RE.match(cursor)
    if not m:
        log.warning("tce_sp.invalid_cursor", cursor=cursor)
        return 0, _DEFAULT_YEAR, 1
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def _next_cursor(
    muni_idx: int, year: int, month: int, total_munis: int
) -> Optional[str]:
    """Advance to the next (muni, year, month) slot; return None when done."""
    if month < 12:
        return f"m{muni_idx}y{year}m{month + 1}"
    if muni_idx + 1 < total_munis:
        return f"m{muni_idx + 1}y{year}m{1}"
    return None


async def _ensure_municipios() -> list[str]:
    """Fetch and cache the list of SP municipality codes from TCE-SP."""
    global _sp_municipios_cache  # noqa: PLW0603
    if _sp_municipios_cache is not None:
        return _sp_municipios_cache

    log.info("tce_sp.fetching_municipios")
    async with tce_sp_client() as client:
        resp = await client.get("/municipios")
        resp.raise_for_status()
        body = resp.json()

    # API returns a list of objects; extract the code/id used in URL paths.
    if isinstance(body, list):
        codes = [
            str(item.get("codigo") or item.get("id") or item.get("nome") or "")
            for item in body
            if item
        ]
        codes = [c for c in codes if c]
    else:
        codes = []

    if not codes:
        log.warning("tce_sp.no_municipios_returned, using fallback")
        codes = ["SAO_PAULO"]

    _sp_municipios_cache = codes
    log.info("tce_sp.municipios_loaded", count=len(codes))
    return codes


# ── Connector ───────────────────────────────────────────────────────────────


class TCESPConnector(BaseConnector):
    """Connector for TCE-SP — Tribunal de Contas do Estado de São Paulo."""

    @property
    def name(self) -> str:
        return "tce_sp"

    def list_jobs(self) -> list[JobSpec]:
        return [
            JobSpec(
                name="tce_sp_despesas",
                description="Monthly municipal expenses from TCE-SP",
                domain="despesa_municipal",
                enabled=True,
            ),
            JobSpec(
                name="tce_sp_receitas",
                description="Monthly municipal revenues from TCE-SP",
                domain="receita_municipal",
                enabled=True,
            ),
        ]

    # ── fetch ───────────────────────────────────────────────────────────────

    async def fetch(
        self,
        job: JobSpec,
        cursor: Optional[str] = None,
        params: Optional[dict] = None,
    ) -> tuple[list[RawItem], Optional[str]]:
        municipios = await _ensure_municipios()
        muni_idx, year, month = _parse_cursor(cursor)

        if muni_idx >= len(municipios):
            return [], None

        municipio = municipios[muni_idx]

        if job.name == "tce_sp_despesas":
            items = await self._fetch_despesas(municipio, year, month, muni_idx)
        elif job.name == "tce_sp_receitas":
            items = await self._fetch_receitas(municipio, year, month, muni_idx)
        else:
            raise ValueError(f"Unknown TCE-SP job: {job.name}")

        next_cur = _next_cursor(muni_idx, year, month, len(municipios))
        return items, next_cur

    async def _fetch_despesas(
        self, municipio: str, year: int, month: int, muni_idx: int
    ) -> list[RawItem]:
        path = f"/despesas/{municipio}/{year}/{month}"
        log.debug("tce_sp.fetch_despesas", municipio=municipio, year=year, month=month)

        async with tce_sp_client() as client:
            resp = await client.get(path)
            resp.raise_for_status()
            body = resp.json()

        records: list[dict] = body if isinstance(body, list) else []
        return [
            RawItem(
                raw_id=f"tce_sp_despesas:m{muni_idx}y{year}m{month}:{i}",
                data=record,
            )
            for i, record in enumerate(records)
        ]

    async def _fetch_receitas(
        self, municipio: str, year: int, month: int, muni_idx: int
    ) -> list[RawItem]:
        path = f"/receitas/{municipio}/{year}/{month}"
        log.debug("tce_sp.fetch_receitas", municipio=municipio, year=year, month=month)

        async with tce_sp_client() as client:
            resp = await client.get(path)
            resp.raise_for_status()
            body = resp.json()

        records: list[dict] = body if isinstance(body, list) else []
        return [
            RawItem(
                raw_id=f"tce_sp_receitas:m{muni_idx}y{year}m{month}:{i}",
                data=record,
            )
            for i, record in enumerate(records)
        ]

    # ── normalize ───────────────────────────────────────────────────────────

    def normalize(
        self,
        job: JobSpec,
        raw_items: list[RawItem],
        params: Optional[dict] = None,
    ) -> NormalizeResult:
        if job.name == "tce_sp_despesas":
            return self._normalize_despesas(raw_items)
        if job.name == "tce_sp_receitas":
            return self._normalize_receitas(raw_items)
        raise ValueError(f"Unknown TCE-SP job: {job.name}")

    def _normalize_despesas(self, raw_items: list[RawItem]) -> NormalizeResult:
        entities: list[CanonicalEntity] = []
        events: list[CanonicalEvent] = []

        for item in raw_items:
            d = item.data
            municipio_nome: str = (d.get("municipio") or "").strip()
            exercicio: str = str(d.get("exercicio") or "")
            mes: str = str(d.get("mes") or "")

            # Municipality entity (buyer)
            muni_entity = CanonicalEntity(
                source_connector="tce_sp",
                source_id=f"municipio:{municipio_nome}",
                type="org",
                name=municipio_nome or "Município desconhecido",
                identifiers={},
                attrs={"uf": "SP"},
            )
            entities.append(muni_entity)

            # Supplier entity (from empenho)
            credor: str = (d.get("credor") or "").strip()
            cnpj_credor: str = (d.get("cnpj_credor") or "").strip()
            supplier_entity: Optional[CanonicalEntity] = None

            if credor or cnpj_credor:
                supplier_source_id = cnpj_credor or credor or item.raw_id
                supplier_type = "company" if len(cnpj_credor) >= 14 else "person"
                identifiers: dict = {}
                if cnpj_credor:
                    identifiers["cnpj" if len(cnpj_credor) >= 14 else "cpf"] = cnpj_credor
                supplier_entity = CanonicalEntity(
                    source_connector="tce_sp",
                    source_id=supplier_source_id,
                    type=supplier_type,
                    name=credor or "Credor desconhecido",
                    identifiers=identifiers,
                )
                entities.append(supplier_entity)

            # Monetary values
            valor_pago = _parse_brl_string(d.get("valor_pago"))
            valor_empenhado = _parse_brl_string(d.get("valor_empenhado"))
            valor_liquidado = _parse_brl_string(d.get("valor_liquidado"))
            event_value = valor_pago if valor_pago is not None else valor_empenhado

            # Participants
            participants: list[CanonicalEventParticipant] = [
                CanonicalEventParticipant(entity_ref=muni_entity, role="buyer"),
            ]
            if supplier_entity is not None:
                participants.append(
                    CanonicalEventParticipant(entity_ref=supplier_entity, role="supplier"),
                )

            event = CanonicalEvent(
                source_connector="tce_sp",
                source_id=item.raw_id,
                type="despesa_municipal",
                subtype="despesa",
                value_brl=event_value,
                attrs={
                    "municipio": municipio_nome,
                    "exercicio": exercicio,
                    "mes": mes,
                    "funcao": (d.get("funcao") or "").strip(),
                    "subfuncao": (d.get("subfuncao") or "").strip(),
                    "credor": credor,
                    "cnpj_credor": cnpj_credor,
                    "valor_empenhado": valor_empenhado,
                    "valor_pago": valor_pago,
                    "valor_liquidado": valor_liquidado,
                },
                participants=participants,
            )
            events.append(event)

        return NormalizeResult(entities=entities, events=events)

    def _normalize_receitas(self, raw_items: list[RawItem]) -> NormalizeResult:
        entities: list[CanonicalEntity] = []
        events: list[CanonicalEvent] = []

        for item in raw_items:
            d = item.data
            municipio_nome: str = (d.get("municipio") or "").strip()
            exercicio: str = str(d.get("exercicio") or "")
            mes: str = str(d.get("mes") or "")

            muni_entity = CanonicalEntity(
                source_connector="tce_sp",
                source_id=f"municipio:{municipio_nome}",
                type="org",
                name=municipio_nome or "Município desconhecido",
                identifiers={},
                attrs={"uf": "SP"},
            )
            entities.append(muni_entity)

            valor_arrecadado = _parse_brl_string(d.get("valor_arrecadado"))

            event = CanonicalEvent(
                source_connector="tce_sp",
                source_id=item.raw_id,
                type="receita_municipal",
                subtype="receita",
                value_brl=valor_arrecadado,
                attrs={
                    "municipio": municipio_nome,
                    "exercicio": exercicio,
                    "mes": mes,
                    "fonte_receita": (d.get("fonte_receita") or "").strip(),
                    "valor_arrecadado": valor_arrecadado,
                },
                participants=[
                    CanonicalEventParticipant(entity_ref=muni_entity, role="org"),
                ],
            )
            events.append(event)

        return NormalizeResult(entities=entities, events=events)

    # ── rate limit ──────────────────────────────────────────────────────────

    def rate_limit_policy(self) -> RateLimitPolicy:
        return RateLimitPolicy(requests_per_second=5, burst=10)
