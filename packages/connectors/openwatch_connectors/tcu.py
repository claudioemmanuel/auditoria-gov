"""Connector for TCU — Tribunal de Contas da Uniao.

Covers:
  - Inidoneos: companies/persons declared ineligible for government contracts.
  - Inabilitados: individuals barred from public office.
  - Acordaos: TCU audit rulings/decisions.

Pagination:
  - Inidoneos/Inabilitados: offset-based, page_size=100. Cursor = str(offset).
  - Acordaos: inicio-based, page_size=50. Cursor = str(inicio).
  When len(returned items) < page_size -> no next cursor (all items fetched).
"""

from datetime import datetime, timezone
from typing import Optional

import httpx

from openwatch_connectors.base import BaseConnector, JobSpec, RateLimitPolicy
from openwatch_connectors.http_client import tcu_contas_client, tcu_dados_client
from openwatch_models.canonical import (
    CanonicalEntity,
    CanonicalEvent,
    CanonicalEventParticipant,
    NormalizeResult,
)
from openwatch_models.raw import RawItem

_INIDONEOS_PAGE_SIZE = 100
_INABILITADOS_PAGE_SIZE = 100
_ACORDAOS_PAGE_SIZE = 50


def _parse_any_datetime(value: object) -> Optional[datetime]:
    if not value:
        return None
    raw = str(value).strip()
    if not raw:
        return None

    for fmt in (
        "%d/%m/%Y",
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
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


class TCUConnector(BaseConnector):
    """Connector for TCU — Tribunal de Contas da Uniao."""

    @property
    def name(self) -> str:
        return "tcu"

    def list_jobs(self) -> list[JobSpec]:
        return [
            JobSpec(
                name="tcu_inidoneos",
                description="Companies/persons declared ineligible for gov contracts by TCU",
                domain="sancao_tcu",
                enabled=True,
            ),
            JobSpec(
                name="tcu_inabilitados",
                description="Individuals barred from public office by TCU",
                domain="sancao_tcu",
                enabled=True,
            ),
            JobSpec(
                name="tcu_acordaos",
                description="TCU audit rulings/decisions",
                domain="acordao_tcu",
                enabled=True,
            ),
        ]

    async def fetch(
        self,
        job: JobSpec,
        cursor: Optional[str] = None,
        params: Optional[dict] = None,
    ) -> tuple[list[RawItem], Optional[str]]:
        offset = int(cursor) if cursor else 0

        if job.name == "tcu_inidoneos":
            return await self._fetch_inidoneos(offset)
        if job.name == "tcu_inabilitados":
            return await self._fetch_inabilitados(offset)
        if job.name == "tcu_acordaos":
            return await self._fetch_acordaos(offset)

        raise ValueError(f"Unknown TCU job: {job.name}")

    async def _fetch_inidoneos(
        self, offset: int
    ) -> tuple[list[RawItem], Optional[str]]:
        async with tcu_contas_client() as client:
            response = await client.get(
                "/ords/condenacao/consulta/inidoneos",
                params={"offset": offset, "limit": _INIDONEOS_PAGE_SIZE},
            )
            response.raise_for_status()
            body: dict = response.json() or {}

        items_data: list[dict] = body.get("items", []) if body else []
        items = [
            RawItem(raw_id=f"tcu_inidoneos:{offset}:{i}", data=r)
            for i, r in enumerate(items_data)
        ]
        next_cursor = (
            str(offset + _INIDONEOS_PAGE_SIZE)
            if len(items_data) >= _INIDONEOS_PAGE_SIZE
            else None
        )
        return items, next_cursor

    async def _fetch_inabilitados(
        self, offset: int
    ) -> tuple[list[RawItem], Optional[str]]:
        async with tcu_contas_client() as client:
            response = await client.get(
                "/ords/condenacao/consulta/inabilitados",
                params={"offset": offset, "limit": _INABILITADOS_PAGE_SIZE},
            )
            response.raise_for_status()
            body: dict = response.json() or {}

        items_data: list[dict] = body.get("items", []) if body else []
        items = [
            RawItem(raw_id=f"tcu_inabilitados:{offset}:{i}", data=r)
            for i, r in enumerate(items_data)
        ]
        next_cursor = (
            str(offset + _INABILITADOS_PAGE_SIZE)
            if len(items_data) >= _INABILITADOS_PAGE_SIZE
            else None
        )
        return items, next_cursor

    async def _fetch_acordaos(
        self, inicio: int
    ) -> tuple[list[RawItem], Optional[str]]:
        async with tcu_dados_client() as client:
            response = await client.get(
                "/api/acordao/recupera-acordaos",
                params={"inicio": inicio, "quantidade": _ACORDAOS_PAGE_SIZE},
            )
            response.raise_for_status()
            body = response.json()

        items_data: list[dict] = body if isinstance(body, list) else []
        items = [
            RawItem(raw_id=f"tcu_acordaos:{inicio}:{i}", data=r)
            for i, r in enumerate(items_data)
        ]
        next_cursor = (
            str(inicio + _ACORDAOS_PAGE_SIZE)
            if len(items_data) >= _ACORDAOS_PAGE_SIZE
            else None
        )
        return items, next_cursor

    def normalize(
        self,
        job: JobSpec,
        raw_items: list[RawItem],
        params: Optional[dict] = None,
    ) -> NormalizeResult:
        if job.name in ("tcu_inidoneos", "tcu_inabilitados"):
            return self._normalize_sancao(job, raw_items)
        if job.name == "tcu_acordaos":
            return self._normalize_acordaos(raw_items)
        raise ValueError(f"Unknown TCU job: {job.name}")

    def _normalize_sancao(
        self, job: JobSpec, raw_items: list[RawItem]
    ) -> NormalizeResult:
        subtype = "inidoneo" if job.name == "tcu_inidoneos" else "inabilitado"
        entities: list[CanonicalEntity] = []
        events: list[CanonicalEvent] = []

        for item in raw_items:
            d = item.data
            nome: str = (d.get("nome") or "").strip()
            # Inidoneos uses cpf_cnpj; inabilitados uses cpf
            cpf_cnpj: str = (d.get("cpf_cnpj") or d.get("cpf") or "").strip()
            processo: str = (d.get("processo") or "").strip()
            source_id = cpf_cnpj or processo or item.raw_id

            if len(cpf_cnpj) == 14:
                entity_type = "company"
                identifiers: dict = {"cnpj": cpf_cnpj}
            elif cpf_cnpj:
                entity_type = "person"
                identifiers = {"cpf": cpf_cnpj}
            else:
                entity_type = "person"
                identifiers = {}

            entity = CanonicalEntity(
                source_connector="tcu",
                source_id=source_id,
                type=entity_type,
                name=nome,
                identifiers=identifiers,
            )
            entities.append(entity)

            sanction_start = _parse_any_datetime(d.get("data_transito_julgado"))
            raw_end = d.get("data_final")
            sanction_end = _parse_any_datetime(raw_end) if raw_end else None

            event = CanonicalEvent(
                source_connector="tcu",
                source_id=item.raw_id,
                type=job.domain,
                subtype=subtype,
                occurred_at=_parse_any_datetime(d.get("data_acordao")),
                attrs={
                    "sanction_start": sanction_start.isoformat() if sanction_start else None,
                    "sanction_end": sanction_end.isoformat() if sanction_end else None,
                    "processo": processo,
                    "deliberacao": (d.get("deliberacao") or "").strip(),
                    "uf": (d.get("uf") or "").strip(),
                    "municipio": d.get("municipio") or None,
                },
                participants=[
                    CanonicalEventParticipant(entity_ref=entity, role="sanctioned")
                ],
            )
            events.append(event)

        return NormalizeResult(entities=entities, events=events)

    def _normalize_acordaos(self, raw_items: list[RawItem]) -> NormalizeResult:
        events: list[CanonicalEvent] = []

        for item in raw_items:
            d = item.data
            event = CanonicalEvent(
                source_connector="tcu",
                source_id=item.raw_id,
                type="acordao_tcu",
                description=d.get("titulo") or None,
                occurred_at=_parse_any_datetime(d.get("dataSessao")),
                attrs={
                    "numero": (d.get("numeroAcordao") or "").strip(),
                    "anoAcordao": (d.get("anoAcordao") or "").strip(),
                    "colegiado": (d.get("colegiado") or "").strip(),
                    "relator": (d.get("relator") or "").strip(),
                    "situacao": (d.get("situacao") or "").strip(),
                    "url_acordao": d.get("urlAcordao") or None,
                },
            )
            events.append(event)

        return NormalizeResult(events=events)

    def rate_limit_policy(self) -> RateLimitPolicy:
        return RateLimitPolicy(requests_per_second=5, burst=10)
