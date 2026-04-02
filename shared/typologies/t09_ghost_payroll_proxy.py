import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from shared.models.orm import Entity, Event, EventParticipant
from shared.models.signals import (
    EvidenceRef,
    RefType,
    RiskSignalOut,
    SignalSeverity,
)
from shared.typologies.base import BaseTypology


class T09GhostPayrollProxyTypology(BaseTypology):
    """T09 — Ghost Payroll Proxy.

    Algorithm:
    1. Anomalous payroll line items:
       a. Unusually high number of distinct benefit/allowance codes.
       b. Values that are exact multiples or round numbers.
       c. Sudden jumps in total compensation vs prior months.
    2. Cross-reference with other data:
       a. Servant listed in multiple organs simultaneously.
       b. Compensation without corresponding position/role.
    3. Checklist scoring (0-1 per factor), composite > 0.7 → signal.
    4. Severity: HIGH if composite > 0.7, CRITICAL if > 0.8.

    Note: This is a PROXY indicator — requires human review.
    """

    @property
    def id(self) -> str:
        return "T09"

    @property
    def name(self) -> str:
        return "Proxy de Folha Fantasma"

    @property
    def required_domains(self) -> list[str]:
        return ["remuneracao"]

    @property
    def required_fields(self) -> list[str]:
        return ["total_compensation", "benefit_codes", "organ_id"]

    async def run(self, session) -> list[RiskSignalOut]:
        window_start, window_end = await self.resolve_window(session, self.required_domains)

        # Query remuneration events
        stmt = (
            select(Event)
            .where(
                Event.type == "remuneracao",
                Event.occurred_at >= window_start,
                Event.occurred_at <= window_end,
            )
        )
        result = await session.execute(stmt)
        events = result.scalars().all()

        if not events:
            return []

        # Get participants (servants)
        event_ids = [e.id for e in events]
        part_stmt = select(EventParticipant).where(
            EventParticipant.event_id.in_(event_ids),
            EventParticipant.role.in_(["servant", "employee", "beneficiary"]),
        )
        part_result = await session.execute(part_stmt)
        participants = part_result.scalars().all()

        # Group events by entity (servant)
        entity_events: dict[str, list[Event]] = defaultdict(list)
        event_map: dict[str, Event] = {str(e.id): e for e in events}
        for p in participants:
            evt = event_map.get(str(p.event_id))
            if evt:
                entity_events[str(p.entity_id)].append(evt)

        # Detect multi-organ servants
        entity_organs: dict[str, set[str]] = defaultdict(set)
        for p in participants:
            evt = event_map.get(str(p.event_id))
            if evt:
                organ = evt.attrs.get("organ_id") or evt.attrs.get("organ_name") or evt.source_connector
                entity_organs[str(p.entity_id)].add(organ)

        signals: list[RiskSignalOut] = []

        for entity_id_str, servant_events in entity_events.items():
            if not servant_events:
                continue

            factor_scores: list[float] = []
            factor_details: dict[str, float] = {}

            # Factor 1: Multiple organs simultaneously
            organs = entity_organs.get(entity_id_str, set())
            multi_organ_score = 0.0
            if len(organs) >= 4:
                multi_organ_score = 0.9
            elif len(organs) >= 3:
                multi_organ_score = 0.7
            elif len(organs) >= 2:
                multi_organ_score = 0.3
            factor_details["multi_organ_score"] = multi_organ_score
            factor_scores.append(multi_organ_score)

            # Factor 2: Round number values (suspicious pattern)
            values = [e.value_brl for e in servant_events if e.value_brl]
            round_count = sum(1 for v in values if v > 0 and v == round(v, -2))
            round_score = 0.0
            if values:
                round_ratio = round_count / len(values)
                if round_ratio > 0.8:
                    round_score = 0.8
                elif round_ratio > 0.5:
                    round_score = 0.5
            factor_details["round_number_score"] = round_score
            factor_scores.append(round_score)

            # Factor 3: Sudden compensation jumps
            sorted_events = sorted(
                servant_events,
                key=lambda e: e.occurred_at or datetime.min.replace(tzinfo=timezone.utc),
            )
            jump_score = 0.0
            if len(sorted_events) >= 2:
                prev_val = sorted_events[0].value_brl or 0
                for e in sorted_events[1:]:
                    curr_val = e.value_brl or 0
                    if prev_val > 0 and curr_val > prev_val * 2:
                        jump_score = max(jump_score, 0.8)
                    elif prev_val > 0 and curr_val > prev_val * 1.5:
                        jump_score = max(jump_score, 0.5)
                    prev_val = curr_val
            factor_details["compensation_jump_score"] = jump_score
            factor_scores.append(jump_score)

            # Factor 4: High number of distinct benefit codes
            all_benefit_codes: set[str] = set()
            for e in servant_events:
                codes = e.attrs.get("benefit_codes", [])
                if isinstance(codes, list):
                    all_benefit_codes.update(codes)
            benefit_score = 0.0
            if len(all_benefit_codes) > 10:
                benefit_score = 0.8
            elif len(all_benefit_codes) > 6:
                benefit_score = 0.5
            factor_details["benefit_codes_score"] = benefit_score
            factor_scores.append(benefit_score)

            # Composite score
            weights = [0.35, 0.20, 0.25, 0.20]
            composite = sum(s * w for s, w in zip(factor_scores, weights))

            if composite < 0.7:
                continue

            if composite > 0.8:
                severity = SignalSeverity.CRITICAL
                confidence = min(0.90, composite)
            else:
                severity = SignalSeverity.HIGH
                confidence = min(0.80, composite)

            total_compensation = sum(v for v in values) if values else 0

            signal = RiskSignalOut(
                id=uuid.uuid4(),
                typology_code=self.id,
                typology_name=self.name,
                severity=severity,
                confidence=confidence,
                title="Indicadores de folha fantasma",
                summary=(
                    f"Score composto {composite:.2f}. "
                    f"Servidor em {len(organs)} órgão(s), "
                    f"{len(servant_events)} registro(s) de remuneração, "
                    f"total R$ {total_compensation:,.2f}."
                ),
                factors={
                    "composite_score": round(composite, 4),
                    "n_organs": len(organs),
                    "n_records": len(servant_events),
                    "total_compensation_brl": round(total_compensation, 2),
                    "n_benefit_codes": len(all_benefit_codes),
                    **{k: round(v, 4) for k, v in factor_details.items()},
                },
                evidence_refs=[
                    EvidenceRef(
                        ref_type=RefType.ENTITY,
                        ref_id=entity_id_str,
                        description="Servidor com indicadores anômalos",
                    ),
                ],
                entity_ids=[uuid.UUID(entity_id_str)],
                event_ids=[e.id for e in servant_events[:20]],
                period_start=window_start,
                period_end=window_end,
                created_at=datetime.now(timezone.utc),
            )
            signals.append(signal)

        return signals
