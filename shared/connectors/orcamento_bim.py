"""File-backed connector for deterministic BIM budget items.

This connector ingests JSONL lines and normalizes them into `orcamento_bim`
events consumed by T23.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Optional

from shared.config import settings
from shared.connectors.base import BaseConnector, JobSpec, RateLimitPolicy
from shared.logging import log
from shared.models.canonical import (
    CanonicalEntity,
    CanonicalEvent,
    CanonicalEventParticipant,
    NormalizeResult,
)
from shared.models.raw import RawItem

_DEFAULT_PAGE_SIZE = 1000


def _safe_float(value: object) -> Optional[float]:
    if value is None:
        return None
    raw = str(value).strip().replace(",", ".")
    if not raw:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _parse_any_datetime(value: object) -> Optional[datetime]:
    if not value:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y%m%d", "%d/%m/%Y"):
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


class OrcamentoBIMConnector(BaseConnector):
    @property
    def name(self) -> str:
        return "orcamento_bim"

    def list_jobs(self) -> list[JobSpec]:
        return [
            JobSpec(
                name="orcamento_bim_items",
                description="BIM unit-cost items aligned with SINAPI references",
                domain="orcamento_bim",
                supports_incremental=True,
                enabled=True,
            ),
        ]

    async def fetch(
        self,
        job: JobSpec,
        cursor: Optional[str] = None,
        params: Optional[dict] = None,
    ) -> tuple[list[RawItem], Optional[str]]:
        if job.name != "orcamento_bim_items":
            raise ValueError(f"Unknown job: {job.name}")

        data_file = str((params or {}).get("data_file") or settings.ORCAMENTO_BIM_DATA_FILE)
        page_size = int((params or {}).get("page_size", _DEFAULT_PAGE_SIZE))
        if page_size <= 0:
            raise ValueError("orcamento_bim page_size must be > 0")

        start_line = int(cursor or "0")
        if start_line < 0:
            raise ValueError("orcamento_bim cursor must be >= 0")

        if not os.path.exists(data_file):
            log.warning("orcamento_bim.file_missing", path=data_file, job=job.name)
            return [], None

        items: list[RawItem] = []
        last_line_index = start_line - 1
        reached_limit = False

        with open(data_file, "r", encoding="utf-8") as f:
            for line_index, raw_line in enumerate(f):
                if line_index < start_line:
                    continue
                last_line_index = line_index

                line = raw_line.strip()
                if not line:
                    continue

                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    log.warning(
                        "orcamento_bim.invalid_jsonl_line",
                        path=data_file,
                        line_number=line_index + 1,
                    )
                    continue

                items.append(RawItem(raw_id=f"{job.name}:{line_index}", data=payload))
                if len(items) >= page_size:
                    reached_limit = True
                    break

        next_cursor = str(last_line_index + 1) if reached_limit else None
        return items, next_cursor

    def normalize(
        self,
        job: JobSpec,
        raw_items: list[RawItem],
        params: Optional[dict] = None,
    ) -> NormalizeResult:
        if job.name != "orcamento_bim_items":
            return NormalizeResult()

        entities: list[CanonicalEntity] = []
        events: list[CanonicalEvent] = []

        for item in raw_items:
            data = item.data or {}

            orgao_cnpj = str(data.get("orgao_cnpj") or data.get("buyer_cnpj") or "").strip()
            orgao_nome = str(data.get("orgao_nome") or data.get("buyer_name") or "").strip()
            fornecedor_cnpj = str(data.get("fornecedor_cnpj") or data.get("supplier_cnpj") or "").strip()
            fornecedor_nome = str(data.get("fornecedor_nome") or data.get("supplier_name") or "").strip()

            sinapi_ref = _safe_float(data.get("sinapi_reference_brl"))
            contracted_unit = _safe_float(data.get("contracted_unit_price_brl"))
            quantity = _safe_float(data.get("quantity")) or 1.0

            value_brl = _safe_float(data.get("value_brl"))
            if value_brl is None and contracted_unit is not None:
                value_brl = contracted_unit * quantity

            participants: list[CanonicalEventParticipant] = []

            if orgao_cnpj or orgao_nome:
                orgao = CanonicalEntity(
                    source_connector=self.name,
                    source_id=orgao_cnpj or f"{item.raw_id}:orgao",
                    type="org",
                    name=orgao_nome or orgao_cnpj,
                    identifiers={"cnpj": orgao_cnpj} if orgao_cnpj else {},
                )
                entities.append(orgao)
                participants.append(CanonicalEventParticipant(entity_ref=orgao, role="buyer"))
                participants.append(
                    CanonicalEventParticipant(entity_ref=orgao, role="procuring_entity"),
                )

            if fornecedor_cnpj or fornecedor_nome:
                fornecedor = CanonicalEntity(
                    source_connector=self.name,
                    source_id=fornecedor_cnpj or f"{item.raw_id}:fornecedor",
                    type="company",
                    name=fornecedor_nome or fornecedor_cnpj,
                    identifiers={"cnpj": fornecedor_cnpj} if fornecedor_cnpj else {},
                )
                entities.append(fornecedor)
                participants.append(CanonicalEventParticipant(entity_ref=fornecedor, role="supplier"))

            occurred_at = _parse_any_datetime(
                data.get("occurred_at") or data.get("data_assinatura") or data.get("date"),
            )
            service_code = str(data.get("service_code") or "").strip()
            obra_id = str(data.get("obra_id") or "").strip()

            events.append(
                CanonicalEvent(
                    source_connector=self.name,
                    source_id=item.raw_id,
                    type="orcamento_bim",
                    subtype=service_code,
                    description=str(data.get("description") or obra_id or "orcamento_bim_item"),
                    occurred_at=occurred_at,
                    value_brl=value_brl,
                    attrs={
                        "sinapi_reference_brl": sinapi_ref,
                        "contracted_unit_price_brl": contracted_unit,
                        "quantity": quantity,
                        "service_code": service_code,
                        "obra_id": obra_id or str(item.raw_id),
                    },
                    participants=participants,
                ),
            )

        return NormalizeResult(entities=entities, events=events)

    def rate_limit_policy(self) -> RateLimitPolicy:
        # Local file connector; no outbound API calls.
        return RateLimitPolicy(requests_per_second=100, burst=100)
