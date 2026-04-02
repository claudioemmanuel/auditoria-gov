import uuid
from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy import select

from openwatch_models.orm import Event, EventParticipant
from openwatch_models.signals import (
    EvidenceRef,
    RefType,
    RiskSignalOut,
    SignalSeverity,
)
from openwatch_typologies.base import BaseTypology


class T22PoliticalFavoritismTypology(BaseTypology):
    """T22 — Favorecimento Politico.

    Legal basis: CF/88 Art. 14, §9°; Lei 9.504/1997, Art. 28 + Art. 81;
    Res. TSE 23.604/2019 (prestacao de contas eleitorais — fonte dos dados de doacao);
    FATF Recomendacao 12 (PEP due diligence).

    Algorithm:
    1. Query events with type == "doacao_eleitoral" in 5-year window
       (source_connector == "tse"; role "donor" = company, "recipient" = politician).
    2. If 0 doacao_eleitoral events found → return [] (TSE data not yet loaded).
    3. Query events with type == "contrato" in 5-year window
       (role "buyer" = procuring entity, "supplier" = company).
    4. For each donor company:
       - Find their contrato events as supplier.
       - For each (donation, contract) pair where donation_date < contract_date
         AND delta_months <= 24: register as a signal candidate pair.
    5. Group by company: emit signal if company has >= 2 such pairs.
    6. Severity: HIGH if avg_delta_months <= 12, MEDIUM if 13–24.
    """

    @property
    def id(self) -> str:
        return "T22"

    @property
    def name(self) -> str:
        return "Favorecimento Politico"

    @property
    def required_domains(self) -> list[str]:
        return ["licitacao", "doacao_eleitoral"]

    @property
    def corruption_types(self) -> list[str]:
        return ["nepotismo_clientelismo", "corrupcao_ativa_passiva"]

    @property
    def spheres(self) -> list[str]:
        return ["politica", "privada"]

    @property
    def evidence_level(self) -> str:
        return "indirect"

    async def run(self, session) -> list[RiskSignalOut]:
        window_start, window_end = await self.resolve_window(session, self.required_domains)

        # Step 1: Query doacao_eleitoral events
        donation_stmt = select(Event).where(
            Event.type == "doacao_eleitoral",
            Event.occurred_at >= window_start,
            Event.occurred_at <= window_end,
        )
        donation_result = await session.execute(donation_stmt)
        donation_events = donation_result.scalars().all()

        # Step 2: early exit if TSE data not yet loaded
        if not donation_events:
            return []

        donation_ids = [e.id for e in donation_events]

        # Step 3: Query contrato events
        contract_stmt = select(Event).where(
            Event.type == "contrato",
            Event.occurred_at >= window_start,
            Event.occurred_at <= window_end,
        )
        contract_result = await session.execute(contract_stmt)
        contract_events = contract_result.scalars().all()

        if not contract_events:
            return []

        contract_ids = [e.id for e in contract_events]

        # Step 4a: Get participants for donation events
        don_part_stmt = select(EventParticipant).where(
            EventParticipant.event_id.in_(donation_ids),
        )
        don_part_result = await session.execute(don_part_stmt)
        donation_participants = don_part_result.scalars().all()

        # Step 4b: Get participants for contract events
        con_part_stmt = select(EventParticipant).where(
            EventParticipant.event_id.in_(contract_ids),
        )
        con_part_result = await session.execute(con_part_stmt)
        contract_participants = con_part_result.scalars().all()

        # Build lookup: entity_id -> list of donation events where they are donor
        donor_to_donations: dict[str, list[Event]] = defaultdict(list)
        donation_event_map: dict[str, Event] = {str(e.id): e for e in donation_events}

        for p in donation_participants:
            if p.role in {"donor", "doador"}:
                eid = str(p.event_id)
                entity_id = str(p.entity_id)
                if eid in donation_event_map:
                    donor_to_donations[entity_id].append(donation_event_map[eid])

        if not donor_to_donations:
            return []

        # Build lookup: entity_id -> list of contract events where they are supplier
        supplier_to_contracts: dict[str, list[Event]] = defaultdict(list)
        contract_event_map: dict[str, Event] = {str(e.id): e for e in contract_events}

        for p in contract_participants:
            if p.role in {"supplier", "winner"}:
                eid = str(p.event_id)
                entity_id = str(p.entity_id)
                if eid in contract_event_map:
                    supplier_to_contracts[entity_id].append(contract_event_map[eid])

        signals: list[RiskSignalOut] = []

        # Step 4: For each donor company, find matching (donation → contract) pairs
        for company_id, donations in donor_to_donations.items():
            contracts = supplier_to_contracts.get(company_id)
            if not contracts:
                continue

            qualifying_pairs: list[tuple[Event, Event, float]] = []
            for donation in donations:
                if donation.occurred_at is None:
                    continue
                for contract in contracts:
                    if contract.occurred_at is None:
                        continue
                    delta = contract.occurred_at - donation.occurred_at
                    delta_days = delta.total_seconds() / 86400.0
                    # donation must precede contract and be within 24 months
                    if 0 < delta_days <= 730:  # 730 days ≈ 24 months
                        delta_months = delta_days / 30.44
                        qualifying_pairs.append((donation, contract, delta_months))

            # Step 5: Emit signal only if >= 2 qualifying pairs
            if len(qualifying_pairs) < 2:
                continue

            delta_months_list = [dm for _, _, dm in qualifying_pairs]
            avg_delta_months = sum(delta_months_list) / len(delta_months_list)

            # Step 6: Severity
            if avg_delta_months <= 12:
                severity = SignalSeverity.HIGH
                confidence = 0.72
            else:
                severity = SignalSeverity.MEDIUM
                confidence = 0.58

            # Collect aggregate stats
            total_donation_brl = sum(
                (d.value_brl or 0.0) for d, _, _ in qualifying_pairs
            )
            total_contract_value_brl = sum(
                (c.value_brl or 0.0) for _, c, _ in qualifying_pairs
            )
            earliest_donation = min(
                d.occurred_at for d, _, _ in qualifying_pairs
                if d.occurred_at is not None
            )
            latest_contract = max(
                c.occurred_at for _, c, _ in qualifying_pairs
                if c.occurred_at is not None
            )

            try:
                company_uuid = uuid.UUID(company_id)
                entity_ids = [company_uuid]
            except ValueError:
                entity_ids = []

            all_event_ids: list[uuid.UUID] = []
            for d, c, _ in qualifying_pairs[:10]:
                for ev in (d, c):
                    try:
                        all_event_ids.append(uuid.UUID(str(ev.id)))
                    except ValueError:
                        pass

            evidence_refs = [
                EvidenceRef(
                    ref_type=RefType.EVENT,
                    ref_id=str(d.id),
                    description=(
                        f"Doação em {d.occurred_at.strftime('%d/%m/%Y') if d.occurred_at else 'N/A'}"
                        f" → contrato em {c.occurred_at.strftime('%d/%m/%Y') if c.occurred_at else 'N/A'}"
                        f" ({dm:.1f} meses)"
                    ),
                )
                for d, c, dm in qualifying_pairs[:5]
            ]

            signal = RiskSignalOut(
                id=uuid.uuid4(),
                typology_code=self.id,
                typology_name=self.name,
                severity=severity,
                confidence=confidence,
                title=(
                    f"Possível favorecimento político — {len(qualifying_pairs)} "
                    f"par(es) doação→contrato (média {avg_delta_months:.1f} meses)"
                ),
                summary=(
                    f"Empresa com {len(qualifying_pairs)} ocorrência(s) de doação "
                    f"eleitoral seguida de contrato público em até 24 meses. "
                    f"Média de intervalo: {avg_delta_months:.1f} meses. "
                    f"Total doado: R$ {total_donation_brl:,.2f}. "
                    f"Total contratado: R$ {total_contract_value_brl:,.2f}."
                ),
                factors={
                    "company_entity_id": company_id,
                    "n_donation_contract_pairs": len(qualifying_pairs),
                    "avg_delta_months": round(avg_delta_months, 2),
                    "total_donation_brl": round(total_donation_brl, 2),
                    "total_contract_value_brl": round(total_contract_value_brl, 2),
                    "earliest_donation_date": earliest_donation.isoformat(),
                    "latest_contract_date": latest_contract.isoformat(),
                },
                evidence_refs=evidence_refs,
                entity_ids=entity_ids,
                event_ids=all_event_ids[:20],
                period_start=window_start,
                period_end=window_end,
                created_at=datetime.now(timezone.utc),
            )
            signals.append(signal)

        return signals
