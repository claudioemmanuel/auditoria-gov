import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from shared.baselines.models import BaselineType
from shared.models.orm import Event, EventParticipant
from shared.models.signals import (
    EvidenceRef,
    RefType,
    RiskSignalOut,
    SignalSeverity,
)
from shared.repo.queries import get_baseline
from shared.typologies.base import BaseTypology


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


class T05PriceOutlierTypology(BaseTypology):
    """T05 — Price Outlier.

    Algorithm:
    1. For each procurement item with a CATMAT/CATSER code:
       a. Get unit_price from the winning bid.
       b. Compare against BASELINE (PRICE_BY_ITEM for same code).
    2. Flag if unit_price > baseline p95.
    3. Compute overpricing ratio = unit_price / baseline_median.
    4. Severity: CRITICAL if > p99 or ratio > 5x, HIGH if > p95.
    5. Include baseline stats in evidence for transparency.
    """

    @property
    def id(self) -> str:
        return "T05"

    @property
    def name(self) -> str:
        return "Preço Outlier"

    @property
    def required_domains(self) -> list[str]:
        return ["licitacao", "contrato"]

    @property
    def required_fields(self) -> list[str]:
        return ["unit_price", "catmat_code", "quantity"]

    async def run(self, session) -> list[RiskSignalOut]:
        window_end = datetime.now(timezone.utc)
        window_start = window_end - timedelta(days=365)

        # Query events with value_brl
        stmt = (
            select(Event)
            .where(
                Event.type.in_(["licitacao", "contrato"]),
                Event.occurred_at >= window_start,
                Event.occurred_at <= window_end,
                Event.value_brl.isnot(None),
                Event.value_brl > 0,
            )
        )
        result = await session.execute(stmt)
        events = result.scalars().all()

        if not events:
            return []

        # Query participants for entity_ids
        all_event_ids = [e.id for e in events]
        parts_stmt = select(EventParticipant).where(
            EventParticipant.event_id.in_(all_event_ids),
            EventParticipant.role.in_(
                ["procuring_entity", "buyer", "supplier", "winner"]
            ),
        )
        parts_result = await session.execute(parts_stmt)
        all_participants = parts_result.scalars().all()

        event_entity_ids: dict[str, list] = defaultdict(list)
        _seen: set[tuple[str, str]] = set()
        for p in all_participants:
            eid_str = str(p.event_id)
            entity_str = str(p.entity_id)
            pair = (eid_str, entity_str)
            if pair not in _seen:
                _seen.add(pair)
                event_entity_ids[eid_str].append(p.entity_id)

        signals: list[RiskSignalOut] = []

        # Group by catmat/catser code for baseline comparison
        for e in events:
            catmat = _normalize_catmat_group(e.attrs.get("catmat_code") or e.attrs.get("catmat_group"))
            if not catmat:
                continue

            unit_price = e.attrs.get("unit_price") or e.value_brl
            if not unit_price or unit_price <= 0:
                continue

            # Get baseline for this item
            scope_key = f"catmat_group::{catmat}"
            baseline = await get_baseline(
                session,
                BaselineType.PRICE_BY_ITEM.value,
                scope_key,
            )

            if baseline is None:
                continue

            p95 = baseline.get("p95", 0)
            p99 = baseline.get("p99", 0)
            median = baseline.get("median", 0)

            if p95 <= 0 or median <= 0:
                continue

            if unit_price <= p95:
                continue

            # Compute overpricing ratio
            overpricing_ratio = unit_price / median

            # Determine severity
            if unit_price > p99 or overpricing_ratio > 5.0:
                severity = SignalSeverity.CRITICAL
                confidence = min(0.98, 0.8 + (overpricing_ratio - 5) * 0.02)
            else:
                severity = SignalSeverity.HIGH
                confidence = min(0.92, 0.6 + (unit_price - p95) / p95 * 0.3)

            catmat_display = "Nao informado pela fonte" if catmat == "nao_informado" else catmat
            description = e.description or f"Item CATMAT {catmat_display}"
            quantity = e.attrs.get("quantity", "N/A")

            signal = RiskSignalOut(
                id=uuid.uuid4(),
                typology_code=self.id,
                typology_name=self.name,
                severity=severity,
                confidence=confidence,
                title=f"Sobrepreço detectado — {catmat_display}",
                summary=(
                    f"Preço unitário R$ {unit_price:,.2f} está "
                    f"{overpricing_ratio:.1f}x acima da mediana (R$ {median:,.2f}) "
                    f"para {description}. "
                    f"Baseline p95=R$ {p95:,.2f}, p99=R$ {p99:,.2f}."
                ),
                factors={
                    "unit_price": round(unit_price, 2),
                    "overpricing_ratio": round(overpricing_ratio, 2),
                    "baseline_median": round(median, 2),
                    "baseline_p95": round(p95, 2),
                    "baseline_p99": round(p99, 2),
                    "catmat_code": catmat,
                    "quantity": quantity,
                    "sample_size": baseline.get("sample_size", 0),
                },
                evidence_refs=[
                    EvidenceRef(
                        ref_type=RefType.EVENT,
                        ref_id=str(e.id),
                        description=f"Evento com preço R$ {unit_price:,.2f}",
                    ),
                    EvidenceRef(
                        ref_type=RefType.BASELINE,
                        description=(
                            f"Baseline PRICE_BY_ITEM para {catmat}: "
                            f"mediana=R$ {median:,.2f}, p95=R$ {p95:,.2f}, "
                            f"p99=R$ {p99:,.2f}, n={baseline.get('sample_size', 0)}"
                        ),
                    ),
                ],
                entity_ids=event_entity_ids.get(str(e.id), []),
                event_ids=[e.id],
                period_start=window_start,
                period_end=window_end,
                created_at=datetime.now(timezone.utc),
            )
            signals.append(signal)

        return signals
