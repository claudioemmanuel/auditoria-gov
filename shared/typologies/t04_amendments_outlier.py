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
from shared.utils.query import execute_chunked_in


class T04AmendmentsOutlierTypology(BaseTypology):
    """T04 — Contract Amendment Outlier.

    Algorithm:
    1. For each contract with amendments (aditivos):
       a. Compute pct_increase = sum(amendment_values) / original_value.
    2. Compare against BASELINE (AMENDMENT_DISTRIBUTION for same modality/scope).
    3. Flag if pct_increase > baseline p95.
    4. Also flag if number of amendments > 5 (administrative red flag).
    5. Severity: CRITICAL if > p99 or > 100% increase, HIGH if > p95.
    """

    @property
    def id(self) -> str:
        return "T04"

    @property
    def name(self) -> str:
        return "Aditivo Outlier"

    @property
    def required_domains(self) -> list[str]:
        return ["contrato"]

    @property
    def required_fields(self) -> list[str]:
        return ["original_value", "amendment_value", "amendment_count"]

    async def run(self, session) -> list[RiskSignalOut]:
        window_end = datetime.now(timezone.utc)
        window_start = window_end - timedelta(days=365 * 5)  # 5-year window to cover historical ingest

        # Query contracts
        stmt = (
            select(Event)
            .where(
                Event.type == "contrato",
                Event.occurred_at >= window_start,
                Event.occurred_at <= window_end,
            )
        )
        result = await session.execute(stmt)
        contracts = result.scalars().all()

        if not contracts:
            return []

        # Query participants for entity_ids
        contract_ids = [c.id for c in contracts]
        all_participants = await execute_chunked_in(
            session,
            lambda batch: select(EventParticipant).where(
                EventParticipant.event_id.in_(batch),
                EventParticipant.role.in_(
                    ["procuring_entity", "buyer", "supplier", "winner"]
                ),
            ),
            contract_ids,
        )

        event_entity_ids: dict[str, list] = defaultdict(list)
        _seen: set[tuple[str, str]] = set()
        for p in all_participants:
            eid_str = str(p.event_id)
            entity_str = str(p.entity_id)
            pair = (eid_str, entity_str)
            if pair not in _seen:
                _seen.add(pair)
                event_entity_ids[eid_str].append(p.entity_id)

        # Get baseline
        baseline = await get_baseline(
            session,
            BaselineType.AMENDMENT_DISTRIBUTION.value,
            "national::all",
        )
        p95 = baseline.get("p95", 0.5) if baseline else 0.5
        p99 = baseline.get("p99", 1.0) if baseline else 1.0

        signals: list[RiskSignalOut] = []

        for c in contracts:
            original_value = c.attrs.get("original_value") or c.value_brl
            amendments_total = c.attrs.get("amendments_total_value", 0)
            amendment_count = c.attrs.get("amendment_count", 0)

            if not original_value or original_value <= 0:
                continue
            if amendments_total <= 0 and amendment_count <= 0:
                continue

            pct_increase = amendments_total / original_value if amendments_total else 0

            # Check thresholds
            should_flag = pct_increase > p95 or amendment_count > 5

            if not should_flag:
                continue

            # Determine severity
            if pct_increase > p99 or pct_increase > 1.0:
                severity = SignalSeverity.CRITICAL
                confidence = min(0.95, 0.8 + pct_increase * 0.05)
            elif pct_increase > p95 or amendment_count > 5:
                severity = SignalSeverity.HIGH
                confidence = max(0.60, min(0.88, 0.6 + (pct_increase - p95) * 2))
            else:
                severity = SignalSeverity.MEDIUM
                confidence = 0.60

            total_value = original_value + amendments_total

            signal = RiskSignalOut(
                id=uuid.uuid4(),
                typology_code=self.id,
                typology_name=self.name,
                severity=severity,
                confidence=confidence,
                title=f"Aditivos excessivos — {pct_increase:.0%} de acréscimo",
                summary=(
                    f"Contrato com {amendment_count} aditivo(s), "
                    f"acréscimo de {pct_increase:.1%} sobre valor original "
                    f"R$ {original_value:,.2f}. "
                    f"Valor total: R$ {total_value:,.2f}. "
                    f"Baseline p95={p95:.1%}, p99={p99:.1%}."
                ),
                factors={
                    "original_value_brl": round(original_value, 2),
                    "amendments_total_brl": round(amendments_total, 2),
                    "amendment_count": amendment_count,
                    "pct_increase": round(pct_increase, 4),
                    "total_value_brl": round(total_value, 2),
                    "baseline_p95": round(p95, 4),
                    "baseline_p99": round(p99, 4),
                },
                evidence_refs=[
                    EvidenceRef(
                        ref_type=RefType.EVENT,
                        ref_id=str(c.id),
                        description=(
                            f"Contrato R$ {original_value:,.2f} + "
                            f"R$ {amendments_total:,.2f} em aditivos"
                        ),
                    ),
                    EvidenceRef(
                        ref_type=RefType.BASELINE,
                        description=f"Baseline p95={p95:.1%}, p99={p99:.1%}",
                    ),
                ],
                entity_ids=event_entity_ids.get(str(c.id), []),
                event_ids=[c.id],
                period_start=c.occurred_at,
                period_end=window_end,
                created_at=datetime.now(timezone.utc),
            )
            signals.append(signal)

        return signals
