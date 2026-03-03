import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from shared.models.orm import Entity, Event, EventParticipant
from shared.utils.query import execute_chunked_in
from shared.models.signals import (
    EvidenceRef,
    RefType,
    RiskSignalOut,
    SignalSeverity,
)
from shared.typologies.base import BaseTypology


class T06ShellCompanyProxyTypology(BaseTypology):
    """T06 — Shell Company Proxy.

    Algorithm (multi-factor checklist):
    1. Rapid volume: company created < 2 years ago + high contract volume.
    2. Incompatible object: CNAE codes inconsistent with procurement objects.
    3. Network traits:
       a. Shared address/phone/partners with other suppliers to same entity.
       b. Graph connectivity: high edge weight to few procuring entities.
    4. Diligence checklist:
       a. No website / social media presence.
       b. Minimum capital vs contract value ratio.
    5. Score each factor 0-1, composite > 0.7 → signal.
    6. Severity: CRITICAL if composite > 0.9, HIGH if > 0.7.
    """

    @property
    def id(self) -> str:
        return "T06"

    @property
    def name(self) -> str:
        return "Proxy de Empresa de Fachada"

    @property
    def required_domains(self) -> list[str]:
        return ["licitacao", "empresa"]

    @property
    def required_fields(self) -> list[str]:
        return ["cnpj", "founding_date", "cnae_codes", "capital"]

    async def run(self, session) -> list[RiskSignalOut]:
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(days=365 * 2)

        # Get companies that have won contracts
        winner_stmt = select(EventParticipant).where(
            EventParticipant.role.in_(["winner", "supplier", "contractor"]),
        )
        winner_result = await session.execute(winner_stmt)
        winners = winner_result.scalars().all()

        if not winners:
            return []

        # Group by entity_id -> events
        entity_events: dict[str, list[uuid.UUID]] = defaultdict(list)
        for w in winners:
            entity_events[str(w.entity_id)].append(w.event_id)

        # Load winning entities with their details (chunked to avoid asyncpg param limit)
        entity_ids = [uuid.UUID(eid) for eid in entity_events.keys()]
        entities = await execute_chunked_in(
            session,
            lambda batch: select(Entity).where(
                Entity.id.in_(batch),
                Entity.type == "company",
            ),
            entity_ids,
        )

        if not entities:
            return []

        # Load contract values
        all_event_ids = set()
        for evts in entity_events.values():
            all_event_ids.update(evts)

        # Chunked query to avoid asyncpg 32 767 param limit
        event_rows = await execute_chunked_in(
            session,
            lambda batch: select(Event).where(
                Event.id.in_(batch),
                Event.value_brl.isnot(None),
            ),
            list(all_event_ids),
        )
        event_map: dict[str, Event] = {str(e.id): e for e in event_rows}

        # Build address index for shared-address detection
        address_entities: dict[str, list[str]] = defaultdict(list)
        phone_entities: dict[str, list[str]] = defaultdict(list)
        for e in entities:
            addr = e.attrs.get("address", "").strip()
            if addr and len(addr) > 10:
                address_entities[addr].append(str(e.id))
            phone = e.attrs.get("telefone", "").strip()
            if phone and len(phone) > 7:
                phone_entities[phone].append(str(e.id))

        signals: list[RiskSignalOut] = []

        for entity in entities:
            eid = str(entity.id)
            event_ids_for_entity = entity_events.get(eid, [])
            if not event_ids_for_entity:
                continue

            # Compute contract totals
            total_contract_value = sum(
                (event_map.get(str(evid), None) or Event(value_brl=0)).value_brl or 0
                for evid in event_ids_for_entity
            )

            factors_detail: dict[str, float] = {}
            factor_scores: list[float] = []

            # Factor 1: Company age (< 2 years = suspicious)
            data_abertura = entity.attrs.get("data_abertura")
            age_score = 0.0
            if data_abertura:
                try:
                    founded = datetime.fromisoformat(str(data_abertura))
                    age_days = (now - founded).days
                    if age_days < 365:
                        age_score = 1.0
                    elif age_days < 730:
                        age_score = 0.7
                    elif age_days < 1095:
                        age_score = 0.3
                except (ValueError, TypeError):
                    pass
            factors_detail["age_score"] = age_score
            factor_scores.append(age_score)

            # Factor 2: Capital vs contract value ratio
            capital = entity.attrs.get("capital_social", 0)
            capital_score = 0.0
            if isinstance(capital, (int, float)) and capital > 0 and total_contract_value > 0:
                ratio = total_contract_value / capital
                if ratio > 100:
                    capital_score = 1.0
                elif ratio > 50:
                    capital_score = 0.8
                elif ratio > 10:
                    capital_score = 0.5
                elif ratio > 5:
                    capital_score = 0.3
            elif capital == 0 and total_contract_value > 0:
                capital_score = 0.8
            factors_detail["capital_score"] = capital_score
            factor_scores.append(capital_score)

            # Factor 3: Shared address with other suppliers
            address = entity.attrs.get("address", "").strip()
            shared_addr_score = 0.0
            shared_entities: list[str] = []
            if address and len(address) > 10:
                co_located = address_entities.get(address, [])
                others = [x for x in co_located if x != eid]
                if len(others) >= 3:
                    shared_addr_score = 1.0
                elif len(others) >= 1:
                    shared_addr_score = 0.6
                shared_entities = others[:5]
            factors_detail["shared_address_score"] = shared_addr_score
            factor_scores.append(shared_addr_score)

            # Factor 4: Shared phone
            phone = entity.attrs.get("telefone", "").strip()
            shared_phone_score = 0.0
            if phone and len(phone) > 7:
                co_phone = phone_entities.get(phone, [])
                others_phone = [x for x in co_phone if x != eid]
                if len(others_phone) >= 1:
                    shared_phone_score = 0.8
            factors_detail["shared_phone_score"] = shared_phone_score
            factor_scores.append(shared_phone_score)

            # Factor 5: Volume relative to company size
            n_contracts = len(event_ids_for_entity)
            volume_score = 0.0
            if n_contracts > 20:
                volume_score = 0.8
            elif n_contracts > 10:
                volume_score = 0.5
            elif n_contracts > 5:
                volume_score = 0.3
            factors_detail["volume_score"] = volume_score
            factor_scores.append(volume_score)

            # Composite score (weighted)
            weights = [0.25, 0.25, 0.20, 0.15, 0.15]
            composite = sum(s * w for s, w in zip(factor_scores, weights))

            if composite < 0.7:
                continue

            if composite > 0.9:
                severity = SignalSeverity.CRITICAL
                confidence = min(0.95, composite)
            else:
                severity = SignalSeverity.HIGH
                confidence = min(0.88, composite)

            signal = RiskSignalOut(
                id=uuid.uuid4(),
                typology_code=self.id,
                typology_name=self.name,
                severity=severity,
                confidence=confidence,
                title=f"Indicadores de empresa de fachada — {entity.name[:60]}",
                summary=(
                    f"Score composto {composite:.2f}. "
                    f"Empresa com {n_contracts} contrato(s), "
                    f"valor total R$ {total_contract_value:,.2f}. "
                    f"Capital social: R$ {capital:,.2f}."
                ),
                factors={
                    "composite_score": round(composite, 4),
                    "n_contracts": n_contracts,
                    "total_contract_value_brl": round(total_contract_value, 2),
                    "capital_social": capital,
                    "shared_address_entities": shared_entities,
                    **{k: round(v, 4) for k, v in factors_detail.items()},
                },
                evidence_refs=[
                    EvidenceRef(
                        ref_type=RefType.ENTITY,
                        ref_id=eid,
                        description=f"Empresa {entity.name}",
                    ),
                ],
                entity_ids=[entity.id],
                event_ids=event_ids_for_entity[:20],
                period_start=window_start,
                period_end=now,
                created_at=now,
            )
            signals.append(signal)

        return signals
