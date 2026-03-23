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

# LC 123/2006 Art. 3°: ME ≤ R$ 4.8M receita bruta; EPP ≤ R$ 78M
_ME_EPP_MEI_PORTES = frozenset({"ME", "EPP", "MEI", "micro", "micro_empresa", "empresa_pequeno_porte"})
# Minimum exclusive lots won by same entity in same organ to flag fictitious ME pattern
_MIN_LOTS_FICTITIOUS = 3


class T24MeEppQuotaFraudTypology(BaseTypology):
    """T24 — Fraude em Cota ME/EPP.

    Legal basis:
    - LC 123/2006, Art. 47-49 (cotas reservadas a ME/EPP em licitações até R$ 80K por item)
    - Lei 14.133/2021, Art. 48 (manutenção do regime de cotas)
    - Decreto 8.538/2015 (regulamentação de participação de ME/EPP)
    - Lei 8.429/1992, Art. 11 (improbidade administrativa — ato de desonestidade)

    Algorithm:
    1. Query licitacao events with attrs.me_epp_exclusive=True or attrs.cota_reservada_me_epp=True
       in 5-year window.
    2. If no exclusive-lot events found → return [] (data not yet loaded).
    3. Find winner participants for those events.
    4. For each winner entity: check porte_empresa attr.
       - If porte not in {ME, EPP, MEI} → CRITICAL signal (large company in reserved lot).
    5. For entities with unknown porte: if same entity wins >= 3 exclusive lots in same orgao
       in 12 months → HIGH signal (fictitious ME pattern by volume).
    """

    @property
    def id(self) -> str:
        return "T24"

    @property
    def name(self) -> str:
        return "Fraude em Cota ME/EPP"

    @property
    def required_domains(self) -> list[str]:
        return ["licitacao"]

    @property
    def corruption_types(self) -> list[str]:
        return ["fraude_licitatoria"]

    @property
    def spheres(self) -> list[str]:
        return ["administrativa", "privada"]

    @property
    def evidence_level(self) -> str:
        return "direct"

    async def run(self, session) -> list[RiskSignalOut]:
        window_end = datetime.now(timezone.utc)
        window_start = window_end - timedelta(days=365 * 5)

        # Step 1: Query exclusive licitacao events
        stmt = select(Event).where(
            Event.type == "licitacao",
            Event.occurred_at >= window_start,
            Event.occurred_at <= window_end,
        )
        result = await session.execute(stmt)
        all_licitacao = result.scalars().all()

        exclusive_events = [
            e for e in all_licitacao
            if e.attrs.get("me_epp_exclusive") is True
            or e.attrs.get("cota_reservada_me_epp") is True
        ]

        # Step 2: Early exit if no ME/EPP exclusive lot data
        if not exclusive_events:
            return []

        excl_ids = [e.id for e in exclusive_events]
        excl_map = {str(e.id): e for e in exclusive_events}

        # Step 3: Get winner participants for exclusive events
        part_stmt = select(EventParticipant).where(
            EventParticipant.event_id.in_(excl_ids),
            EventParticipant.role == "winner",
        )
        part_result = await session.execute(part_stmt)
        winner_participants = part_result.scalars().all()

        if not winner_participants:
            return []

        # Collect unique winner entity IDs
        winner_entity_ids = list({str(p.entity_id) for p in winner_participants})

        # Step 4: Load entity records for winners
        entity_stmt = select(Entity).where(
            Entity.id.in_([
                uuid.UUID(eid) for eid in winner_entity_ids
            ])
        )
        entity_result = await session.execute(entity_stmt)
        entities = {str(e.id): e for e in entity_result.scalars().all()}

        signals: list[RiskSignalOut] = []

        # ── GROUP A: Large company winning ME/EPP exclusive lot ───────────────
        for p in winner_participants:
            entity_id = str(p.entity_id)
            event = excl_map.get(str(p.event_id))
            if event is None:
                continue
            entity = entities.get(entity_id)
            if entity is None:
                continue
            porte = str(entity.attrs.get("porte_empresa", "")).strip().upper()
            if not porte or porte in {e.upper() for e in _ME_EPP_MEI_PORTES}:
                continue  # legitimate ME/EPP winner or unknown porte

            # Large company in a reserved lot
            try:
                entity_uuid = uuid.UUID(entity_id)
            except ValueError:
                continue

            signal = RiskSignalOut(
                id=uuid.uuid4(),
                typology_code=self.id,
                typology_name=self.name,
                severity=SignalSeverity.CRITICAL,
                confidence=0.85,
                title=(
                    f"Empresa de porte '{porte}' venceu cota reservada a ME/EPP "
                    f"— {event.description or str(event.id)[:8]}"
                ),
                summary=(
                    f"Entidade com porte cadastrado '{porte}' ganhou licitação reservada "
                    f"exclusivamente a microempresas e empresas de pequeno porte (LC 123/2006, "
                    f"Art. 47-49). Valor do lote: "
                    f"R$ {event.value_brl:,.2f}." if event.value_brl else
                    f"Entidade com porte cadastrado '{porte}' ganhou licitação reservada "
                    f"a ME/EPP. Valor não informado."
                ),
                factors={
                    "winner_entity_id": entity_id,
                    "porte_empresa": porte,
                    "event_id": str(event.id),
                    "event_value_brl": event.value_brl,
                    "me_epp_exclusive": True,
                },
                evidence_refs=[
                    EvidenceRef(
                        ref_type=RefType.EVENT,
                        ref_id=str(event.id),
                        description=(
                            f"Licitação exclusiva ME/EPP vencida por empresa de porte '{porte}'"
                        ),
                    )
                ],
                entity_ids=[entity_uuid],
                event_ids=[event.id],
                period_start=window_start,
                period_end=window_end,
                created_at=datetime.now(timezone.utc),
            )
            signals.append(signal)

        # ── GROUP B: Same entity wins >= 3 exclusive lots in same organ ───────
        # Build: orgao_entity -> list of exclusive lot win events
        orgao_winner_wins: dict[tuple[str, str], list[Event]] = defaultdict(list)
        for p in winner_participants:
            entity_id = str(p.entity_id)
            entity = entities.get(entity_id)
            porte = str((entity.attrs.get("porte_empresa", "") if entity else "")).strip().upper()
            # Skip entities already flagged by Group A (they have non-ME porte)
            if porte and porte not in {e.upper() for e in _ME_EPP_MEI_PORTES}:
                continue
            event = excl_map.get(str(p.event_id))
            if event is None:
                continue
            orgao = str(event.attrs.get("orgao_cnpj", event.attrs.get("buyer_cnpj", "")))
            orgao_winner_wins[(orgao, entity_id)].append(event)

        for (orgao, entity_id), win_events in orgao_winner_wins.items():
            # Check within any 12-month window
            if len(win_events) < _MIN_LOTS_FICTITIOUS:
                continue
            win_events_sorted = sorted(
                [e for e in win_events if e.occurred_at is not None],
                key=lambda e: e.occurred_at,
            )
            # Sliding window check
            found_burst = False
            for i, anchor in enumerate(win_events_sorted):
                burst = [
                    e for e in win_events_sorted[i:]
                    if e.occurred_at is not None
                    and (e.occurred_at - anchor.occurred_at).days <= 365
                ]
                if len(burst) >= _MIN_LOTS_FICTITIOUS:
                    found_burst = True
                    break

            if not found_burst:
                continue

            try:
                entity_uuid = uuid.UUID(entity_id)
            except ValueError:
                continue

            total_value = sum((e.value_brl or 0.0) for e in win_events)
            event_ids = [e.id for e in win_events[:20]]
            evidence_refs = [
                EvidenceRef(
                    ref_type=RefType.EVENT,
                    ref_id=str(e.id),
                    description=(
                        f"Cota reservada ME/EPP vencida em "
                        f"{e.occurred_at.strftime('%d/%m/%Y') if e.occurred_at else 'N/A'}"
                    ),
                )
                for e in win_events[:5]
            ]

            signal = RiskSignalOut(
                id=uuid.uuid4(),
                typology_code=self.id,
                typology_name=self.name,
                severity=SignalSeverity.HIGH,
                confidence=0.68,
                title=(
                    f"Possível ME/EPP fictícia — {len(win_events)} cotas exclusivas "
                    f"vencidas no mesmo órgão"
                ),
                summary=(
                    f"Entidade venceu {len(win_events)} licitações com cota reservada a ME/EPP "
                    f"em um mesmo órgão em até 12 meses. Padrão compatível com empresa de "
                    f"fachada constituída para acessar cotas indevidamente. "
                    f"Valor total: R$ {total_value:,.2f}."
                ),
                factors={
                    "winner_entity_id": entity_id,
                    "orgao_cnpj": orgao,
                    "n_exclusive_lots_won": len(win_events),
                    "total_value_brl": round(total_value, 2),
                },
                evidence_refs=evidence_refs,
                entity_ids=[entity_uuid],
                event_ids=event_ids,
                period_start=window_start,
                period_end=window_end,
                created_at=datetime.now(timezone.utc),
            )
            signals.append(signal)

        return signals
