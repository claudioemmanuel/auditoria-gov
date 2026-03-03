"""Connector for Senado Federal.

Senators list: https://legis.senado.leg.br/dadosabertos (Accept: application/json)
CEAPS expenses: https://apis.codante.io/senator-expenses (official endpoint returns 404)
Docs (Codante): https://docs.apis.codante.io/gastos-senadores
"""

from datetime import datetime, timezone
from typing import Optional

from shared.connectors.base import BaseConnector, JobSpec, RateLimitPolicy
from shared.connectors.http_client import senado_client, senado_ceaps_client, DEFAULT_PAGE_SIZE
from shared.models.canonical import (
    CanonicalEntity,
    CanonicalEvent,
    CanonicalEventParticipant,
    NormalizeResult,
)
from shared.models.raw import RawItem


class SenadoConnector(BaseConnector):
    """Connector for Senado Federal (senators + CEAPS expenses)."""

    @property
    def name(self) -> str:
        return "senado"

    def list_jobs(self) -> list[JobSpec]:
        return [
            JobSpec(
                name="senado_senadores",
                description="Senators directory (current legislature)",
                domain="legislativo",
                supports_incremental=False,
                enabled=True,
            ),
            JobSpec(
                name="senado_ceaps",
                description="CEAPS — senator quota expenses (via Codante)",
                domain="despesa",
                enabled=True,
            ),
        ]

    async def fetch(
        self,
        job: JobSpec,
        cursor: Optional[str] = None,
        params: Optional[dict] = None,
    ) -> tuple[list[RawItem], Optional[str]]:
        if job.name == "senado_senadores":
            return await self._fetch_senadores()
        if job.name == "senado_ceaps":
            return await self._fetch_ceaps(cursor, params)
        raise ValueError(f"Unknown job: {job.name}")

    async def _fetch_senadores(self) -> tuple[list[RawItem], Optional[str]]:
        async with senado_client() as client:
            response = await client.get("/senador/lista/atual")
            response.raise_for_status()
            body = response.json()

        parlamentares = (
            body.get("ListaParlamentarEmExercicio", {})
            .get("Parlamentares", {})
            .get("Parlamentar", [])
        )
        if isinstance(parlamentares, dict):
            parlamentares = [parlamentares]

        items = [
            RawItem(raw_id=f"senado_senadores:{i}", data=p)
            for i, p in enumerate(parlamentares)
        ]
        return items, None  # Single-page dump

    async def _fetch_ceaps(
        self, cursor: Optional[str], params: Optional[dict]
    ) -> tuple[list[RawItem], Optional[str]]:
        """Fetch CEAPS expenses from Codante API.

        Endpoint: GET /expenses?year=YYYY&page=N
        Response: {"data": [...], "links": {"next": ...}, "meta": {"current_page": N}}

        Multi-year cursor format: "y{year_idx}p{page}" — iterates 3 years of data.
        """
        # Build 3-year range of years to iterate
        current_year = datetime.now(timezone.utc).year
        years = [str(y) for y in range(current_year - 4, current_year + 1)]

        explicit_ano = (params or {}).get("ano")
        if explicit_ano:
            years = [str(explicit_ano)]

        # Parse cursor
        year_idx, page = 0, 1
        if cursor:
            if cursor.startswith("y") and "p" in cursor:
                parts = cursor[1:].split("p", 1)
                year_idx, page = int(parts[0]), int(parts[1])
            else:
                page = int(cursor)

        if year_idx >= len(years):
            return [], None

        ano = years[year_idx]

        async with senado_ceaps_client() as client:
            response = await client.get(
                "/expenses",
                params={"year": ano, "page": page},
            )
            response.raise_for_status()
            body = response.json()

        records = body.get("data", [])
        items = [
            RawItem(raw_id=f"senado_ceaps:{ano}:{page}:{i}", data=r)
            for i, r in enumerate(records)
        ]

        # Check pagination via links.next or meta; advance year when exhausted
        has_next = bool(body.get("links", {}).get("next"))
        if has_next:
            next_cursor = f"y{year_idx}p{page + 1}"
        elif year_idx + 1 < len(years):
            next_cursor = f"y{year_idx + 1}p1"
        else:
            next_cursor = None
        return items, next_cursor

    def normalize(
        self,
        job: JobSpec,
        raw_items: list[RawItem],
        params: Optional[dict] = None,
    ) -> NormalizeResult:
        if job.name == "senado_senadores":
            return self._normalize_senadores(raw_items)
        if job.name == "senado_ceaps":
            return self._normalize_ceaps(raw_items)
        return NormalizeResult()

    def _normalize_senadores(self, items: list[RawItem]) -> NormalizeResult:
        entities = []
        for item in items:
            d = item.data
            ident = d.get("IdentificacaoParlamentar", d)
            entities.append(
                CanonicalEntity(
                    source_connector="senado",
                    source_id=str(ident.get("CodigoParlamentar", item.raw_id)),
                    type="person",
                    name=ident.get("NomeParlamentar", ident.get("NomeCompletoParlamentar", "")),
                    identifiers={"codigo_parlamentar": str(ident.get("CodigoParlamentar", ""))},
                    attrs={
                        "sigla_partido": ident.get("SiglaPartidoParlamentar", ""),
                        "uf": ident.get("UfParlamentar", ""),
                        "url_foto": ident.get("UrlFotoParlamentar", ""),
                    },
                )
            )
        return NormalizeResult(entities=entities)

    def _normalize_ceaps(self, items: list[RawItem]) -> NormalizeResult:
        entities: list[CanonicalEntity] = []
        events: list[CanonicalEvent] = []

        for item in items:
            d = item.data
            senator_data = d.get("senator", {})
            senator = CanonicalEntity(
                source_connector="senado",
                source_id=str(senator_data.get("id", item.raw_id)),
                type="person",
                name=senator_data.get("name", ""),
                identifiers={"senator_id": str(senator_data.get("id", ""))},
                attrs={
                    "sigla_partido": senator_data.get("party", ""),
                    "uf": senator_data.get("UF", ""),
                },
            )
            entities.append(senator)

            # Supplier entity (if document is present)
            supplier_doc = _digits_only(d.get("supplier_document", ""))
            supplier_name = d.get("supplier", "")
            participants = [
                CanonicalEventParticipant(entity_ref=senator, role="senador"),
                CanonicalEventParticipant(entity_ref=senator, role="buyer"),
            ]
            if supplier_doc:
                supplier_identifiers = (
                    {"cnpj": supplier_doc}
                    if len(supplier_doc) == 14
                    else {"cpf": supplier_doc} if len(supplier_doc) == 11 else {}
                )
                supplier = CanonicalEntity(
                    source_connector="senado",
                    source_id=supplier_doc,
                    type="person" if len(supplier_doc) == 11 else "company",
                    name=supplier_name,
                    identifiers=supplier_identifiers,
                )
                entities.append(supplier)
                participants.append(CanonicalEventParticipant(entity_ref=supplier, role="fornecedor"))
                participants.append(CanonicalEventParticipant(entity_ref=supplier, role="supplier"))

            amount = _safe_float(d.get("amount"))
            occurred_at = _parse_any_datetime(d.get("date"))
            expense_category = d.get("expense_category", "")
            events.append(
                CanonicalEvent(
                    source_connector="senado",
                    source_id=str(d.get("id", d.get("original_id", item.raw_id))),
                    type="despesa",
                    subtype="ceaps",
                    description=expense_category or d.get("description", ""),
                    occurred_at=occurred_at,
                    value_brl=amount,
                    attrs={
                        "date": d.get("date", ""),
                        "description": d.get("description", ""),
                        "modality": "ceaps",
                        "catmat_group": expense_category or "ceaps",
                    },
                    participants=participants,
                )
            )

        return NormalizeResult(entities=entities, events=events)


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
