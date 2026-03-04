"""Connector for Senado Federal.

Senators list: https://legis.senado.leg.br/dadosabertos (Accept: application/json)
CEAPS expenses: https://legis.senado.leg.br/dadosabertos/senador/{codigo}/ceaps
Official docs: https://legis.senado.leg.br/dadosabertos/docs
"""

from datetime import datetime, timezone
from typing import Optional

from shared.connectors.base import BaseConnector, JobSpec, RateLimitPolicy
from shared.connectors.http_client import senado_client, DEFAULT_PAGE_SIZE
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
                description="CEAPS — senator quota expenses (official Senado API)",
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
            body = {} if response.status_code == 204 else response.json()

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
        """Fetch CEAPS expenses from the official Senado API (per senator).

        Strategy: first fetch senator codes via /senador/lista/atual, then
        call GET /senador/{codigo}/ceaps?ano=YYYY for each senator/year.

        Cursor format: "s{senator_idx}y{year_idx}" for resumability.
        """
        current_year = datetime.now(timezone.utc).year
        years = [str(y) for y in range(current_year - 4, current_year + 1)]

        explicit_ano = (params or {}).get("ano")
        if explicit_ano:
            years = [str(explicit_ano)]

        # Fetch senator codes
        senator_codes = await self._get_senator_codes()
        if not senator_codes:
            return [], None

        # Parse cursor
        senator_idx, year_idx = 0, 0
        if cursor:
            if cursor.startswith("s") and "y" in cursor:
                parts = cursor[1:].split("y", 1)
                senator_idx, year_idx = int(parts[0]), int(parts[1])

        if senator_idx >= len(senator_codes):
            return [], None

        codigo = senator_codes[senator_idx]
        ano = years[year_idx]

        async with senado_client() as client:
            response = await client.get(
                f"/senador/{codigo}/ceaps",
                params={"ano": ano},
            )
            response.raise_for_status()
            body = _parse_response(response)

        # Extract CEAPS records — handle both JSON structures
        ceaps = (
            body.get("CesapAtual", body.get("Ceaps", {}))
            .get("Despesas", {})
            .get("Despesa", [])
        )
        if isinstance(ceaps, dict):
            ceaps = [ceaps]

        items = [
            RawItem(
                raw_id=f"senado_ceaps:{codigo}:{ano}:{i}",
                data={**record, "_senator_codigo": str(codigo)},
            )
            for i, record in enumerate(ceaps)
        ]

        # Advance cursor: next year, then next senator
        if year_idx + 1 < len(years):
            next_cursor = f"s{senator_idx}y{year_idx + 1}"
        elif senator_idx + 1 < len(senator_codes):
            next_cursor = f"s{senator_idx + 1}y0"
        else:
            next_cursor = None

        return items, next_cursor

    async def _get_senator_codes(self) -> list[str]:
        """Fetch current senator codes from /senador/lista/atual."""
        async with senado_client() as client:
            response = await client.get("/senador/lista/atual")
            response.raise_for_status()
            body = {} if response.status_code == 204 else response.json()

        parlamentares = (
            body.get("ListaParlamentarEmExercicio", {})
            .get("Parlamentares", {})
            .get("Parlamentar", [])
        )
        if isinstance(parlamentares, dict):
            parlamentares = [parlamentares]

        codes = []
        for p in parlamentares:
            ident = p.get("IdentificacaoParlamentar", p)
            code = ident.get("CodigoParlamentar")
            if code:
                codes.append(str(code))
        return codes

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
            senator_codigo = d.get("_senator_codigo", "")

            senator = CanonicalEntity(
                source_connector="senado",
                source_id=senator_codigo or item.raw_id,
                type="person",
                name=d.get("NomeParlamentar", d.get("Senador", "")),
                identifiers={"codigo_parlamentar": senator_codigo},
                attrs={},
            )
            entities.append(senator)

            # Supplier entity (if document is present)
            supplier_doc = _digits_only(d.get("CNPJCPF", ""))
            supplier_name = d.get("Fornecedor", "")
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

            amount = _safe_float(d.get("ValorReembolsado", d.get("ValorDocumento")))
            occurred_at = _parse_any_datetime(d.get("Data", d.get("DataDoc")))
            expense_category = d.get("TipoDespesa", "")
            events.append(
                CanonicalEvent(
                    source_connector="senado",
                    source_id=f"{senator_codigo}:{d.get('Data', '')}:{d.get('NumeroDocumento', item.raw_id)}",
                    type="despesa",
                    subtype="ceaps",
                    description=expense_category or d.get("Detalhamento", ""),
                    occurred_at=occurred_at,
                    value_brl=amount,
                    attrs={
                        "date": d.get("Data", ""),
                        "description": d.get("Detalhamento", ""),
                        "modality": "ceaps",
                        "catmat_group": expense_category or "ceaps",
                    },
                    participants=participants,
                )
            )

        return NormalizeResult(entities=entities, events=events)


def _parse_response(response: object) -> dict:
    """Parse Senado API response handling both JSON and XML fallback."""
    content_type = getattr(response, "headers", {}).get("content-type", "")
    if response.status_code == 204:
        return {}
    if "xml" in content_type:
        # Senado API sometimes returns XML; extract as best-effort dict
        import xml.etree.ElementTree as ET
        root = ET.fromstring(response.text)
        return _xml_to_dict(root)
    return response.json()


def _xml_to_dict(element: object) -> dict:
    """Recursively convert an XML element to a dict."""
    result: dict = {}
    for child in element:
        tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
        if len(child) > 0:
            child_dict = _xml_to_dict(child)
            if tag in result:
                existing = result[tag]
                if isinstance(existing, list):
                    existing.append(child_dict)
                else:
                    result[tag] = [existing, child_dict]
            else:
                result[tag] = child_dict
        else:
            result[tag] = child.text or ""
    return result


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
