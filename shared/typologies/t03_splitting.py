import uuid
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.orm import DispensaThreshold, Event, EventParticipant
from shared.models.signals import (
    EvidenceRef,
    RefType,
    RiskSignalOut,
    SignalSeverity,
)
from shared.typologies.base import BaseTypology


async def get_dispensa_threshold(
    session: AsyncSession, categoria: str, event_date: date
) -> Decimal:
    """Look up the dispensa threshold valid at the given event_date."""
    result = await session.execute(
        select(DispensaThreshold.valor_brl)
        .where(DispensaThreshold.categoria == categoria)
        .where(DispensaThreshold.valid_from <= event_date)
        .where(
            or_(
                DispensaThreshold.valid_to.is_(None),
                DispensaThreshold.valid_to >= event_date,
            )
        )
        .order_by(DispensaThreshold.valid_from.desc())
        .limit(1)
    )
    row = result.scalar_one_or_none()
    if row is None:
        # Fallback to Decreto 12.343/2024 values if no threshold configured
        fallback = {"goods": Decimal("62725.59"), "works": Decimal("125451.15")}
        return fallback.get(categoria, Decimal("62725.59"))
    return row


# Thresholds for dispensa de licitação (Lei 14.133/2021)
# Updated by Decreto 12.343/2024 (effective 2024)
# Previous values (Decreto 10.922/2021): R$ 50,000 goods/services, R$ 100,000 public works/engineering
# Source: https://www.planalto.gov.br/ccivil_03/_ato2023-2026/2024/decreto/D12343.htm
_DISPENSA_GOODS_THRESHOLD = 62_725.59      # R$ 62,725.59 — goods/services (Decreto 12.343/2024)
_DISPENSA_ENGINEERING_THRESHOLD = 125_451.15  # R$ 125,451.15 — public works/engineering (Decreto 12.343/2024)
_DISPENSA_SERVICES_THRESHOLD = _DISPENSA_ENGINEERING_THRESHOLD  # alias
_DEFAULT_THRESHOLD = _DISPENSA_GOODS_THRESHOLD
_MAX_GAP_DAYS = 30  # Max days between purchases to be considered a cluster

# Keywords that indicate a procurement is for engineering/public works, which
# qualifies for the higher Decreto 12.343/2024 threshold (R$ 125,451.15).
_ENGINEERING_KEYWORDS = {
    "obra", "obras", "engenharia", "construcao", "construção",
    "reforma", "infraestrutura", "pavimentacao", "pavimentação",
}


def _normalize_catmat_group(value: object) -> str:
    text = str(value or "").strip()
    if text.lower() in {
        "",
        "unknown",
        "sem classificacao",
        "sem classificação",
        "null",
        "none",
        "nao_informado",
        "não informado",
    }:
        return "nao_informado"
    return text


def _display_catmat_group(value: str) -> str:
    if value == "nao_informado":
        return "Nao informado pela fonte"
    return value


class T03SplittingTypology(BaseTypology):
    """T03 — Expenditure Splitting (Fracionamento de Despesa).

    Algorithm:
    1. For each procuring entity + CATMAT/CATSER group:
       a. Find direct purchases (dispensa) in temporal sequences.
       b. Identify clusters where cumulative value approaches or exceeds
          the dispensa threshold (R$ 62,725.59 goods/services or
          R$ 125,451.15 engineering/works — Decreto 12.343/2024).
    2. Use semantic clustering on descriptions to detect split purchases
       with slightly different wording.
    3. Flag sequences where:
       - Temporal gap between purchases < 30 days
       - Same or similar object descriptions
       - Cumulative value > threshold
    4. Severity: CRITICAL if > 2x threshold, HIGH if > threshold.
    """

    @property
    def id(self) -> str:
        return "T03"

    @property
    def name(self) -> str:
        return "Fracionamento de Despesa"

    @property
    def required_domains(self) -> list[str]:
        return ["despesa", "licitacao"]

    @property
    def required_fields(self) -> list[str]:
        return ["value_brl", "modality", "description", "occurred_at"]

    async def run(self, session) -> list[RiskSignalOut]:
        window_end = datetime.now(timezone.utc)
        window_start = window_end - timedelta(days=365 * 5)  # 5-year window to cover historical ingest

        # Query dispensa/direct purchase events
        stmt = (
            select(Event)
            .where(
                Event.type.in_(["despesa", "licitacao"]),
                Event.occurred_at >= window_start,
                Event.occurred_at <= window_end,
                Event.value_brl.isnot(None),
                Event.value_brl > 0,
            )
        )
        result = await session.execute(stmt)
        events = result.scalars().all()

        # Filter for dispensa modality.
        # "inexigibilidade" is excluded: it covers technical/artistic sole-source
        # exemptions, NOT price-based direct purchases subject to the dispensa limit.
        # Events with absent/null/empty modality are SKIPPED to avoid false positives
        # from low-value contracts processed under other procurement methods.
        _DISPENSA_MODALITIES = {
            "dispensa", "dispensa de licitacao",
            "dispensa_licitacao", "dispensa_valor", "compra_direta",
            "dispensa_eletronica",
        }
        skipped_unknown_modality = 0
        dispensas = []
        for e in events:
            modality = (e.attrs.get("modality") or "").strip().lower()
            if not modality:
                skipped_unknown_modality += 1
                continue
            if modality in _DISPENSA_MODALITIES:
                dispensas.append(e)

        if not dispensas:
            return []

        # Dispensas canceladas/anuladas não representam gasto real — excluir
        _VOID = frozenset({"deserta", "fracassada", "revogada", "anulada", "cancelada"})
        dispensas = [
            e for e in dispensas
            if e.attrs.get("situacao", "").lower().strip() not in _VOID
        ]

        if not dispensas:
            return []

        # Get procuring entities
        event_ids = [e.id for e in dispensas]
        buyer_stmt = select(EventParticipant).where(
            EventParticipant.event_id.in_(event_ids),
            EventParticipant.role.in_(["procuring_entity", "buyer"]),
        )
        buyer_result = await session.execute(buyer_stmt)
        buyers = buyer_result.scalars().all()

        event_buyer: dict[str, uuid.UUID] = {}
        for b in buyers:
            event_buyer[str(b.event_id)] = b.entity_id

        # Group by (buyer, catmat_group)
        groups: dict[tuple, list[Event]] = defaultdict(list)
        for e in dispensas:
            buyer_id = event_buyer.get(str(e.id), uuid.UUID(int=0))
            catmat = _normalize_catmat_group(
                e.attrs.get("catmat_group") or e.attrs.get("catmat_code")
            )
            groups[(str(buyer_id), catmat)].append(e)

        signals: list[RiskSignalOut] = []

        for key, group_events in groups.items():
            buyer_id_str, catmat = key
            if len(group_events) < 2:
                continue
            # Skip groups with no identifiable buyer — cannot attribute to an organ
            if buyer_id_str == str(uuid.UUID(int=0)):
                continue

            # Sort by date
            sorted_events = sorted(
                group_events, key=lambda e: e.occurred_at or datetime.min.replace(tzinfo=timezone.utc)
            )

            # Find temporal clusters (purchases within MAX_GAP_DAYS of each other)
            clusters: list[list[Event]] = []
            current_cluster: list[Event] = [sorted_events[0]]

            for e in sorted_events[1:]:
                prev_date = current_cluster[-1].occurred_at
                curr_date = e.occurred_at
                if prev_date and curr_date and (curr_date - prev_date).days <= _MAX_GAP_DAYS:
                    current_cluster.append(e)
                else:
                    if len(current_cluster) >= 2:
                        clusters.append(current_cluster)
                    current_cluster = [e]

            if len(current_cluster) >= 2:
                clusters.append(current_cluster)

            # Evaluate each cluster
            for cluster in clusters:
                total_value = sum(e.value_brl or 0 for e in cluster)
                # Use the higher engineering threshold when any event in the cluster
                # is classified as public works / engineering (Decreto 12.343/2024).
                is_engineering = any(
                    any(
                        kw in (
                            (e.attrs.get("object_type") or "")
                            + " " + (e.attrs.get("subtype") or "")
                            + " " + (e.description or "")
                        ).lower()
                        for kw in _ENGINEERING_KEYWORDS
                    )
                    for e in cluster
                )
                threshold = _DISPENSA_ENGINEERING_THRESHOLD if is_engineering else _DISPENSA_GOODS_THRESHOLD

                if total_value <= threshold:
                    continue

                ratio = total_value / threshold

                if ratio > 2.0:
                    severity = SignalSeverity.CRITICAL
                    confidence = min(0.95, 0.75 + (ratio - 2) * 0.05)
                else:
                    severity = SignalSeverity.HIGH
                    confidence = min(0.85, 0.55 + (ratio - 1) * 0.3)

                first_date = cluster[0].occurred_at
                last_date = cluster[-1].occurred_at
                span_days = (last_date - first_date).days if first_date and last_date else 0
                catmat_display = _display_catmat_group(catmat)

                signal = RiskSignalOut(
                    id=uuid.uuid4(),
                    typology_code=self.id,
                    typology_name=self.name,
                    severity=severity,
                    confidence=confidence,
                    title=f"Possível fracionamento — {catmat_display}",
                    summary=(
                        f"{len(cluster)} compras diretas em {span_days} dias, "
                        f"totalizando R$ {total_value:,.2f} "
                        f"({ratio:.1f}x o limite de R$ {threshold:,.2f}). "
                        f"Grupo CATMAT: {catmat_display}."
                    ),
                    factors={
                        "n_purchases": len(cluster),
                        "total_value_brl": round(total_value, 2),
                        "threshold_brl": threshold,
                        "ratio": round(ratio, 2),
                        "span_days": span_days,
                        "catmat_group": catmat,
                        "avg_value_brl": round(total_value / len(cluster), 2),
                        "skipped_unknown_modality": skipped_unknown_modality,
                    },
                    evidence_refs=[
                        EvidenceRef(
                            ref_type=RefType.EVENT,
                            ref_id=str(e.id),
                            description=(
                                f"Compra R$ {e.value_brl:,.2f} em "
                                f"{e.occurred_at.strftime('%d/%m/%Y') if e.occurred_at else 'N/A'}"
                            ),
                        )
                        for e in cluster[:10]
                    ],
                    entity_ids=[uuid.UUID(buyer_id_str)] if buyer_id_str != str(uuid.UUID(int=0)) else [],
                    event_ids=[e.id for e in cluster],
                    period_start=first_date,
                    period_end=last_date,
                    created_at=datetime.now(timezone.utc),
                )
                signals.append(signal)

        return signals
