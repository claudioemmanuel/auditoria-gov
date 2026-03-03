"""Connector for Câmara dos Deputados (dadosabertos.camara.leg.br).

API docs: https://dadosabertos.camara.leg.br/swagger/api.html
Auth: None (public API).
Pagination: `pagina` (1-based), `itens` per page.
"""

from datetime import datetime, timezone
from typing import Optional

from shared.connectors.base import BaseConnector, JobSpec, RateLimitPolicy
from shared.connectors.http_client import camara_client, DEFAULT_PAGE_SIZE
from shared.models.canonical import (
    CanonicalEntity,
    CanonicalEvent,
    CanonicalEventParticipant,
    NormalizeResult,
)
from shared.models.raw import RawItem

_DEPUTIES_PER_PAGE = 100


class CamaraConnector(BaseConnector):
    """Connector for Câmara dos Deputados (dadosabertos.camara.leg.br)."""

    @property
    def name(self) -> str:
        return "camara"

    def list_jobs(self) -> list[JobSpec]:
        return [
            JobSpec(
                name="camara_deputados",
                description="Deputies directory (current legislature)",
                domain="legislativo",
                supports_incremental=False,
                enabled=True,
            ),
            JobSpec(
                name="camara_despesas_cota",
                description="CEAP — parliamentary quota expenses",
                domain="despesa",
                enabled=True,
            ),
            JobSpec(
                name="camara_orgaos",
                description="Committees and organs",
                domain="legislativo",
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
        if job.name == "camara_despesas_cota":
            return await self._fetch_despesas_cota(cursor, params)

        page = int(cursor) if cursor else 1
        query_params: dict = {"pagina": page, "itens": DEFAULT_PAGE_SIZE}

        if job.name == "camara_deputados":
            endpoint = "/deputados"
        elif job.name == "camara_orgaos":
            endpoint = "/orgaos"
        else:
            raise ValueError(f"Unknown job: {job.name}")

        async with camara_client() as client:
            response = await client.get(endpoint, params=query_params)
            response.raise_for_status()
            body = response.json()

        data = body.get("dados", [])
        items = [
            RawItem(raw_id=f"{job.name}:{page}:{i}", data=item)
            for i, item in enumerate(data)
        ]
        next_cursor = str(page + 1) if len(data) >= DEFAULT_PAGE_SIZE else None
        return items, next_cursor

    async def _fetch_despesas_cota(
        self,
        cursor: Optional[str],
        params: Optional[dict],
    ) -> tuple[list[RawItem], Optional[str]]:
        """Fetch CEAP expenses.  Auto-iterates through deputies when no deputado_id.

        Multi-year iteration: covers 3 years of historical data.
        Single-deputy cursor: "y{year_idx}p{page}"
        Auto-discover cursor: "y{year_idx}d{dep_page}:{dep_idx}"
        """
        dep_id = (params or {}).get("deputado_id")

        # Build 3-year range of years to iterate
        current_year = datetime.now(timezone.utc).year
        years = [str(y) for y in range(current_year - 4, current_year + 1)]

        explicit_ano = (params or {}).get("ano")
        if explicit_ano:
            years = [str(explicit_ano)]

        if dep_id:
            # Single-deputy mode (manual trigger)
            # Cursor format: "y{year_idx}p{page}"
            year_idx, page = 0, 1
            if cursor:
                if cursor.startswith("y") and "p" in cursor:
                    parts = cursor[1:].split("p", 1)
                    year_idx, page = int(parts[0]), int(parts[1])
                else:
                    page = int(cursor)

            if year_idx >= len(years):
                return [], None

            current_ano = years[year_idx]

            # Fetch deputy UF from API for single-deputy triggers
            dep_uf_single = ""
            try:
                async with camara_client() as client:
                    resp = await client.get(f"/deputados/{dep_id}")
                    resp.raise_for_status()
                    dep_data = resp.json().get("dados", {})
                    dep_uf_single = dep_data.get("siglaUf", "")
            except Exception:
                pass
            items, inner_next = await self._fetch_deputy_expenses(int(dep_id), current_ano, page, dep_uf=dep_uf_single)

            if inner_next:
                next_cursor = f"y{year_idx}p{inner_next}"
            elif year_idx + 1 < len(years):
                next_cursor = f"y{year_idx + 1}p1"
            else:
                next_cursor = None
            return items, next_cursor

        # Auto-discover mode: iterate through deputies list, across years
        # Cursor format: "y{year_idx}d{dep_list_page}:{dep_index_in_page}"
        year_idx = 0
        if cursor is None:
            dep_page, dep_idx = 1, 0
        elif cursor.startswith("y") and "d" in cursor:
            year_part, dep_part = cursor[1:].split("d", 1)
            year_idx = int(year_part)
            parts = dep_part.split(":")
            dep_page, dep_idx = int(parts[0]), int(parts[1])
        else:
            parts = cursor.split(":")
            dep_page, dep_idx = int(parts[0]), int(parts[1])

        if year_idx >= len(years):
            return [], None

        current_ano = years[year_idx]

        # Fetch current page of deputies
        async with camara_client() as client:
            resp = await client.get(
                "/deputados",
                params={"pagina": dep_page, "itens": _DEPUTIES_PER_PAGE},
            )
            resp.raise_for_status()
            deputies = resp.json().get("dados", [])

        if not deputies or dep_idx >= len(deputies):
            # No more deputies on this page — advance to next year
            if year_idx + 1 < len(years):
                return [], f"y{year_idx + 1}d1:0"
            return [], None

        dep = deputies[dep_idx]
        dep_uf = dep.get("siglaUf", "")
        items, _ = await self._fetch_deputy_expenses(dep["id"], current_ano, 1, dep_uf=dep_uf)

        # Advance cursor to next deputy
        next_idx = dep_idx + 1
        if next_idx >= len(deputies):
            if len(deputies) >= _DEPUTIES_PER_PAGE:
                next_cursor = f"y{year_idx}d{dep_page + 1}:0"
            elif year_idx + 1 < len(years):
                next_cursor = f"y{year_idx + 1}d1:0"
            else:
                next_cursor = None
        else:
            next_cursor = f"y{year_idx}d{dep_page}:{next_idx}"

        return items, next_cursor

    async def _fetch_deputy_expenses(
        self, dep_id: int, ano: str, page: int, dep_uf: str = ""
    ) -> tuple[list[RawItem], Optional[str]]:
        async with camara_client() as client:
            resp = await client.get(
                f"/deputados/{dep_id}/despesas",
                params={"ano": ano, "pagina": page, "itens": DEFAULT_PAGE_SIZE},
            )
            resp.raise_for_status()
            data = resp.json().get("dados", [])

        items = [
            RawItem(
                raw_id=f"camara_despesas_cota:{dep_id}:{page}:{i}",
                data={**d, "_deputado_id": dep_id, "siglaUf": dep_uf},
            )
            for i, d in enumerate(data)
        ]
        next_cursor = str(page + 1) if len(data) >= DEFAULT_PAGE_SIZE else None
        return items, next_cursor

    def normalize(
        self,
        job: JobSpec,
        raw_items: list[RawItem],
        params: Optional[dict] = None,
    ) -> NormalizeResult:
        if job.name == "camara_deputados":
            return self._normalize_deputados(raw_items)
        if job.name == "camara_despesas_cota":
            return self._normalize_despesas(raw_items)
        if job.name == "camara_orgaos":
            return self._normalize_orgaos(raw_items)
        return NormalizeResult()

    def _normalize_deputados(self, items: list[RawItem]) -> NormalizeResult:
        entities = []
        for item in items:
            d = item.data
            entities.append(
                CanonicalEntity(
                    source_connector="camara",
                    source_id=str(d.get("id", item.raw_id)),
                    type="person",
                    name=d.get("nome", ""),
                    identifiers={"deputado_id": str(d.get("id", ""))},
                    attrs={
                        "sigla_partido": d.get("siglaPartido", ""),
                        "sigla_uf": d.get("siglaUf", ""),
                        "url_foto": d.get("urlFoto", ""),
                        "email": d.get("email", ""),
                    },
                )
            )
        return NormalizeResult(entities=entities)

    def _normalize_despesas(self, items: list[RawItem]) -> NormalizeResult:
        entities: list[CanonicalEntity] = []
        events: list[CanonicalEvent] = []
        for item in items:
            d = item.data

            # Deputy entity (person who spends)
            deputado_id = str(d.get("_deputado_id", ""))
            deputy = CanonicalEntity(
                source_connector="camara",
                source_id=deputado_id or f"{item.raw_id}:deputado",
                type="person",
                name="",  # Name not in expense record; resolved via ER
                identifiers={"deputado_id": deputado_id} if deputado_id else {},
            )

            # Supplier entity (company/person that receives payment)
            fornecedor_cnpj_cpf = d.get("cnpjCpfFornecedor", "")
            fornecedor = CanonicalEntity(
                source_connector="camara",
                source_id=fornecedor_cnpj_cpf or f"{item.raw_id}:fornecedor",
                type="company",
                name=d.get("nomeFornecedor", ""),
                identifiers={"cnpj_cpf": fornecedor_cnpj_cpf} if fornecedor_cnpj_cpf else {},
            )

            if deputado_id:
                entities.append(deputy)
            if fornecedor_cnpj_cpf or d.get("nomeFornecedor"):
                entities.append(fornecedor)

            participants = []
            if deputado_id:
                participants.append(
                    CanonicalEventParticipant(entity_ref=deputy, role="buyer")
                )
            if fornecedor_cnpj_cpf or d.get("nomeFornecedor"):
                participants.append(
                    CanonicalEventParticipant(entity_ref=fornecedor, role="supplier")
                )

            events.append(
                CanonicalEvent(
                    source_connector="camara",
                    source_id=item.raw_id,
                    type="despesa_cota",
                    description=d.get("tipoDespesa", ""),
                    value_brl=d.get("valorDocumento"),
                    attrs={
                        "ano": d.get("ano"),
                        "mes": d.get("mes"),
                        "fornecedor": d.get("nomeFornecedor", ""),
                        "cnpj_cpf_fornecedor": fornecedor_cnpj_cpf,
                        "valor_liquido": d.get("valorLiquido"),
                        "uf": d.get("sgUF", d.get("siglaUf", "")),
                    },
                    participants=participants,
                )
            )
        return NormalizeResult(entities=entities, events=events)

    def _normalize_orgaos(self, items: list[RawItem]) -> NormalizeResult:
        entities = []
        for item in items:
            d = item.data
            entities.append(
                CanonicalEntity(
                    source_connector="camara",
                    source_id=str(d.get("id", item.raw_id)),
                    type="org",
                    name=d.get("nome", d.get("sigla", "")),
                    attrs={"sigla": d.get("sigla", ""), "tipo": d.get("tipoOrgao", "")},
                )
            )
        return NormalizeResult(entities=entities)
