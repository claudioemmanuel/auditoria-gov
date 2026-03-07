import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from shared.models.orm import Event, EventParticipant
from shared.utils.query import execute_chunked_in
from shared.models.signals import (
    EvidenceRef,
    RefType,
    RiskSignalOut,
    SignalSeverity,
)
from shared.typologies.base import BaseTypology


class T10OutsourcingParallelPayrollTypology(BaseTypology):
    """T10 — Outsourcing Parallel Payroll.

    Algorithm:
    1. Identify long-running outsourcing contracts (> 5 years continuous).
    2. Check supplier concentration:
       a. Same supplier renewed/amended across multiple periods.
       b. Few or no competitive procurements for renewal.
    3. Recurring amendments:
       a. Frequent value increases (> 3 amendments per contract).
       b. Cumulative increase > 50% of original value.
    4. Cross-reference with payroll:
       a. Outsourced positions duplicating existing civil servant roles.
    5. Severity: HIGH if 2+ factors, CRITICAL if 3+.
    """

    @property
    def id(self) -> str:
        return "T10"

    @property
    def name(self) -> str:
        return "Terceirização Paralela"

    @property
    def required_domains(self) -> list[str]:
        return ["contrato", "remuneracao"]

    @property
    def required_fields(self) -> list[str]:
        return ["contract_duration", "amendment_count", "supplier_entity_id"]

    async def run(self, session) -> list[RiskSignalOut]:
        now = datetime.now(timezone.utc)

        # Query outsourcing contracts — use a 10-year window to capture long-duration
        # patterns (5+ years continuous), while still bounding the full-table scan.
        window_start = now - timedelta(days=365 * 10)
        stmt = (
            select(Event)
            .where(
                Event.type == "contrato",
                Event.occurred_at >= window_start,
            )
        )
        result = await session.execute(stmt)
        contracts = result.scalars().all()

        if not contracts:
            return []

        # Get suppliers for contracts (chunked to avoid asyncpg param limit)
        contract_ids = [c.id for c in contracts]
        supplier_parts = await execute_chunked_in(
            session,
            lambda batch: select(EventParticipant).where(
                EventParticipant.event_id.in_(batch),
                EventParticipant.role.in_(["supplier", "contractor"]),
            ),
            contract_ids,
        )

        # Get buyers for contracts (chunked to avoid asyncpg param limit)
        buyer_parts = await execute_chunked_in(
            session,
            lambda batch: select(EventParticipant).where(
                EventParticipant.event_id.in_(batch),
                EventParticipant.role.in_(["procuring_entity", "buyer"]),
            ),
            contract_ids,
        )

        # Map contract -> supplier, buyer
        contract_supplier: dict[str, str] = {}
        contract_buyer: dict[str, str] = {}
        for sp in supplier_parts:
            contract_supplier[str(sp.event_id)] = str(sp.entity_id)
        for bp in buyer_parts:
            contract_buyer[str(bp.event_id)] = str(bp.entity_id)

        # Group contracts by (buyer, supplier)
        pair_contracts: dict[tuple, list[Event]] = defaultdict(list)
        for c in contracts:
            cid = str(c.id)
            supplier = contract_supplier.get(cid)
            buyer = contract_buyer.get(cid)
            if supplier and buyer:
                pair_contracts[(buyer, supplier)].append(c)

        signals: list[RiskSignalOut] = []

        for (buyer_id, supplier_id), pair_events in pair_contracts.items():
            if len(pair_events) < 2:
                continue

            # Sort by date
            sorted_contracts = sorted(
                pair_events,
                key=lambda e: e.occurred_at or datetime.min.replace(tzinfo=timezone.utc),
            )

            factor_count = 0
            factor_details: dict[str, object] = {}

            # Factor 1: Long duration (combined contract span > 5 years)
            first_date = sorted_contracts[0].occurred_at
            last_date = sorted_contracts[-1].occurred_at
            span_days = 0
            if first_date and last_date:
                span_days = (last_date - first_date).days

            long_duration = span_days > 365 * 5
            factor_details["span_days"] = span_days
            factor_details["long_duration"] = long_duration
            if long_duration:
                factor_count += 1

            # Factor 2: Supplier concentration (same supplier across renewals)
            n_contracts = len(pair_events)
            concentration = n_contracts >= 3
            factor_details["n_contracts"] = n_contracts
            factor_details["concentration"] = concentration
            if concentration:
                factor_count += 1

            # Factor 3: Excessive amendments
            total_amendments = sum(
                c.attrs.get("amendment_count", 0) for c in pair_events
            )
            total_original = sum(
                (c.attrs.get("original_value") or c.value_brl or 0)
                for c in pair_events
            )
            total_amendment_value = sum(
                c.attrs.get("amendments_total_value", 0) for c in pair_events
            )
            amendment_pct = (
                total_amendment_value / total_original
                if total_original > 0
                else 0
            )

            excessive_amendments = total_amendments > 3 or amendment_pct > 0.5
            factor_details["total_amendments"] = total_amendments
            factor_details["amendment_pct"] = round(amendment_pct, 4)
            factor_details["excessive_amendments"] = excessive_amendments
            if excessive_amendments:
                factor_count += 1

            # Factor 4: Outsourcing indicator (check contract type/description)
            outsourcing_keywords = [
                "terceirizacao", "terceirização", "mão de obra",
                "mao de obra", "prestação de serviços", "prestacao",
                "limpeza", "vigilância", "vigilancia", "portaria",
                "recepção", "recepcao", "apoio administrativo",
            ]
            outsourcing_flag = False
            for c in pair_events:
                desc = (c.description or "").lower()
                subtype = (c.subtype or "").lower()
                if any(kw in desc or kw in subtype for kw in outsourcing_keywords):
                    outsourcing_flag = True
                    break
            factor_details["outsourcing_flag"] = outsourcing_flag
            if outsourcing_flag:
                factor_count += 1

            # Need at least 2 factors
            if factor_count < 2:
                continue

            if factor_count >= 3:
                severity = SignalSeverity.CRITICAL
                confidence = 0.85
            else:
                severity = SignalSeverity.HIGH
                confidence = 0.70

            total_value = sum(c.value_brl or 0 for c in pair_events)

            signal = RiskSignalOut(
                id=uuid.uuid4(),
                typology_code=self.id,
                typology_name=self.name,
                severity=severity,
                confidence=confidence,
                title="Terceirização paralela detectada",
                summary=(
                    f"{n_contracts} contrato(s) com mesmo fornecedor em "
                    f"{span_days // 365} ano(s). "
                    f"Valor total: R$ {total_value:,.2f}. "
                    f"{total_amendments} aditivo(s) ({amendment_pct:.0%} acréscimo). "
                    f"Fatores: {factor_count}/4."
                ),
                factors={
                    "n_factors": factor_count,
                    "total_value_brl": round(total_value, 2),
                    **{k: v for k, v in factor_details.items()},
                },
                evidence_refs=[
                    EvidenceRef(
                        ref_type=RefType.EVENT,
                        ref_id=str(c.id),
                        description=(
                            f"Contrato R$ {c.value_brl:,.2f}" if c.value_brl
                            else f"Contrato {str(c.id)[:8]}"
                        ),
                    )
                    for c in pair_events[:10]
                ],
                entity_ids=[uuid.UUID(supplier_id), uuid.UUID(buyer_id)],
                event_ids=[c.id for c in pair_events[:20]],
                period_start=first_date,
                period_end=last_date or now,
                created_at=now,
            )
            signals.append(signal)

        return signals
