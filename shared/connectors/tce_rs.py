"""Connector for TCE-RS — Tribunal de Contas do Estado do Rio Grande do Sul.

Covers:
  - Gestão Fiscal: LRF compliance data (revenue, spending, debt).
  - Educação: Education spending compliance indices.
  - Saúde: Health spending compliance indices.

Pagination:
  - No pagination within a year endpoint (returns full year as JSON array).
  - Cursor = year string (e.g. "2024").
  - Iterates from current year back to 5 years ago.
"""

from datetime import datetime, timezone
from typing import Optional

import httpx

from shared.connectors.base import BaseConnector, JobSpec, RateLimitPolicy
from shared.connectors.http_client import tce_rs_client
from shared.models.canonical import (
    CanonicalEntity,
    CanonicalEvent,
    CanonicalEventParticipant,
    NormalizeResult,
)
from shared.models.raw import RawItem

_MIN_YEAR_OFFSET = 5  # fetch up to 5 years back


def _parse_any_datetime(value: object) -> Optional[datetime]:
    """Parse various datetime formats returned by TCE-RS into UTC datetimes."""
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


def _next_cursor(current_year: int) -> Optional[str]:
    """Return next cursor (previous year) or None if we've gone back far enough."""
    min_year = datetime.now(timezone.utc).year - _MIN_YEAR_OFFSET
    prev = current_year - 1
    if prev < min_year:
        return None
    return str(prev)


def _org_entity(codigo_orgao: str, nome_orgao: str) -> CanonicalEntity:
    """Build an org CanonicalEntity from a TCE-RS municipality code."""
    return CanonicalEntity(
        source_connector="tce_rs",
        source_id=codigo_orgao,
        type="org",
        name=nome_orgao,
        identifiers={"tce_rs_codigo": codigo_orgao},
    )


class TCERSConnector(BaseConnector):
    """TCE-RS open-data connector."""

    @property
    def name(self) -> str:
        return "tce_rs"

    def list_jobs(self) -> list[JobSpec]:
        return [
            JobSpec(
                name="tce_rs_gestao_fiscal",
                description="Fiscal management data (LRF compliance) in RS state",
                domain="gestao_fiscal",
                enabled=True,
            ),
            JobSpec(
                name="tce_rs_educacao",
                description="Education spending compliance indices in RS state",
                domain="educacao",
                enabled=True,
            ),
            JobSpec(
                name="tce_rs_saude",
                description="Health spending compliance indices in RS state",
                domain="saude",
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
        year = int(cursor) if cursor else datetime.now(timezone.utc).year

        if job.name == "tce_rs_gestao_fiscal":
            path = f"/dados/municipal/gastos-lrf-mde-asps/{year}.json"
        elif job.name == "tce_rs_educacao":
            path = f"/dados/municipal/educacao-indice/{year}.json"
        elif job.name == "tce_rs_saude":
            path = f"/dados/municipal/saude-indice/{year}.json"
        else:
            raise ValueError(f"Unknown TCE-RS job: {job.name}")

        async with tce_rs_client() as client:
            response = await client.get(path)
            response.raise_for_status()
            body = response.json()

        items_data: list[dict] = body if isinstance(body, list) else []
        items = [
            RawItem(raw_id=f"{job.name}:{year}:{i}", data=r)
            for i, r in enumerate(items_data)
        ]
        return items, _next_cursor(year)

    # ------------------------------------------------------------------
    # normalize
    # ------------------------------------------------------------------

    def normalize(
        self,
        job: JobSpec,
        raw_items: list[RawItem],
        params: Optional[dict] = None,
    ) -> NormalizeResult:
        if job.name == "tce_rs_gestao_fiscal":
            return self._normalize_gestao_fiscal(raw_items)
        if job.name == "tce_rs_educacao":
            return self._normalize_educacao(raw_items)
        if job.name == "tce_rs_saude":
            return self._normalize_saude(raw_items)
        raise ValueError(f"Unknown TCE-RS job: {job.name}")

    # -- gestão fiscal ----------------------------------------------------

    def _normalize_gestao_fiscal(self, raw_items: list[RawItem]) -> NormalizeResult:
        entities: list[CanonicalEntity] = []
        events: list[CanonicalEvent] = []

        for item in raw_items:
            d = item.data
            participants: list[CanonicalEventParticipant] = []

            codigo = _clean(d.get("codigo_orgao"))
            nome = _clean(d.get("nome_orgao")) or "Órgão não identificado"
            if codigo:
                org = _org_entity(codigo, nome)
                entities.append(org)
                participants.append(
                    CanonicalEventParticipant(entity_ref=org, role="responsible_entity")
                )

            despesa_pessoal: Optional[float] = None
            raw_val = d.get("despesa_pessoal")
            if raw_val is not None:
                try:
                    despesa_pessoal = float(raw_val)
                except (TypeError, ValueError):
                    pass

            ano = _clean(d.get("ano"))
            occurred_at = _parse_any_datetime(f"{ano}-01-01") if ano else None

            event = CanonicalEvent(
                source_connector="tce_rs",
                source_id=item.raw_id,
                type="fiscal_compliance",
                subtype="lrf",
                description=f"LRF compliance — {nome} ({ano})" if ano else f"LRF compliance — {nome}",
                occurred_at=occurred_at,
                value_brl=despesa_pessoal,
                attrs={
                    "ano": ano,
                    "receita_corrente_liquida": d.get("receita_corrente_liquida"),
                    "despesa_pessoal": d.get("despesa_pessoal"),
                    "divida_consolidada": d.get("divida_consolidada"),
                    "operacoes_credito": d.get("operacoes_credito"),
                    "receita_mde": d.get("receita_mde"),
                    "despesa_mde": d.get("despesa_mde"),
                    "receita_asps": d.get("receita_asps"),
                    "despesa_asps": d.get("despesa_asps"),
                },
                participants=participants,
            )
            events.append(event)

        return NormalizeResult(entities=entities, events=events)

    # -- educação ---------------------------------------------------------

    def _normalize_educacao(self, raw_items: list[RawItem]) -> NormalizeResult:
        entities: list[CanonicalEntity] = []
        events: list[CanonicalEvent] = []

        for item in raw_items:
            d = item.data
            participants: list[CanonicalEventParticipant] = []

            codigo = _clean(d.get("codigo_orgao"))
            nome = _clean(d.get("nome_orgao")) or "Órgão não identificado"
            if codigo:
                org = _org_entity(codigo, nome)
                entities.append(org)
                participants.append(
                    CanonicalEventParticipant(entity_ref=org, role="responsible_entity")
                )

            valor_despesa: Optional[float] = None
            raw_val = d.get("valor_despesa")
            if raw_val is not None:
                try:
                    valor_despesa = float(raw_val)
                except (TypeError, ValueError):
                    pass

            ano = _clean(d.get("ano"))
            occurred_at = _parse_any_datetime(f"{ano}-01-01") if ano else None

            event = CanonicalEvent(
                source_connector="tce_rs",
                source_id=item.raw_id,
                type="fiscal_compliance",
                subtype="education_spending",
                description=f"Education spending compliance — {nome} ({ano})" if ano else f"Education spending compliance — {nome}",
                occurred_at=occurred_at,
                value_brl=valor_despesa,
                attrs={
                    "ano": ano,
                    "valor_despesa": d.get("valor_despesa"),
                    "valor_receita": d.get("valor_receita"),
                    "indice": d.get("indice"),
                },
                participants=participants,
            )
            events.append(event)

        return NormalizeResult(entities=entities, events=events)

    # -- saúde ------------------------------------------------------------

    def _normalize_saude(self, raw_items: list[RawItem]) -> NormalizeResult:
        entities: list[CanonicalEntity] = []
        events: list[CanonicalEvent] = []

        for item in raw_items:
            d = item.data
            participants: list[CanonicalEventParticipant] = []

            codigo = _clean(d.get("codigo_orgao"))
            nome = _clean(d.get("nome_orgao")) or "Órgão não identificado"
            if codigo:
                org = _org_entity(codigo, nome)
                entities.append(org)
                participants.append(
                    CanonicalEventParticipant(entity_ref=org, role="responsible_entity")
                )

            valor_despesa: Optional[float] = None
            raw_val = d.get("valor_despesa")
            if raw_val is not None:
                try:
                    valor_despesa = float(raw_val)
                except (TypeError, ValueError):
                    pass

            ano = _clean(d.get("ano"))
            occurred_at = _parse_any_datetime(f"{ano}-01-01") if ano else None

            event = CanonicalEvent(
                source_connector="tce_rs",
                source_id=item.raw_id,
                type="fiscal_compliance",
                subtype="health_spending",
                description=f"Health spending compliance — {nome} ({ano})" if ano else f"Health spending compliance — {nome}",
                occurred_at=occurred_at,
                value_brl=valor_despesa,
                attrs={
                    "ano": ano,
                    "valor_despesa": d.get("valor_despesa"),
                    "valor_receita": d.get("valor_receita"),
                    "indice": d.get("indice"),
                },
                participants=participants,
            )
            events.append(event)

        return NormalizeResult(entities=entities, events=events)

    # ------------------------------------------------------------------
    # rate limit
    # ------------------------------------------------------------------

    def rate_limit_policy(self) -> RateLimitPolicy:
        return RateLimitPolicy(requests_per_second=2, burst=4)
