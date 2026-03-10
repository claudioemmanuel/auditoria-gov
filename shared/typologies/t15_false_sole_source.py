import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from shared.baselines.compute import _CATMAT_MISSING
from shared.models.orm import Event, EventParticipant
from shared.models.signals import (
    EvidenceRef,
    RefType,
    RiskSignalOut,
    SignalSeverity,
)
from shared.typologies.base import BaseTypology

_INEXIGIBILIDADE_MODALITIES = {
    "inexigibilidade",
    "inexigibilidade de licitacao",
    "inexigibilidade_licitacao",
    "inexigibilidade_licitação",
}

_COMPETITIVE_MODALITIES = {
    "pregao", "pregão", "concorrencia", "concorrência",
    "tomada_de_precos", "tomada de preços", "convite",
    "leilao", "leilão", "concurso", "dialogo_competitivo",
}

# Minimum number of alternative suppliers to consider competition exists
_MIN_ALTERNATIVE_SUPPLIERS = 3

# Minimum inexigibilidade contracts with same supplier at same agency to flag pattern
_MIN_REPEAT_INEXIGIBILIDADE = 2


class T15FalseSoleSourceTypology(BaseTypology):
    """T15 — Inexigibilidade Indevida (False Sole-Source).

    Algorithm:
    1. Extract all licitacoes with modality = "inexigibilidade".
    2. For each CATMAT/CATSER group in those contracts:
       a. Count distinct suppliers who bid in *competitive* licitacoes
          for the same CATMAT group at any agency.
    3. If ≥ 3 alternative suppliers exist in competitive tenders → flag
       the inexigibilidade as suspicious.
    4. Compound flag: same supplier receiving ≥ 2 inexigibilidade contracts
       at the same agency.
    5. Severity: CRITICAL if n_alternatives ≥ 5 AND repeat ≥ 3; HIGH otherwise.

    Legal basis:
    - Lei 14.133/2021, Art. 74 (sole-source procurement criteria)
    - Lei 8.666/93, Art. 25 (sole-source exemption criteria)
    - Lei 8.429/92, Art. 10, VII (waiving competitive bidding outside legal grounds)
    """

    @property
    def id(self) -> str:
        return "T15"

    @property
    def name(self) -> str:
        return "Inexigibilidade Indevida"

    @property
    def required_domains(self) -> list[str]:
        return ["licitacao"]

    @property
    def required_fields(self) -> list[str]:
        return ["modality", "catmat_group"]

    @property
    def corruption_types(self) -> list[str]:
        return ["fraude_licitatoria", "prevaricacao"]

    @property
    def spheres(self) -> list[str]:
        return ["administrativa"]

    @property
    def evidence_level(self) -> str:
        return "indirect"

    async def run(self, session) -> list[RiskSignalOut]:
        window_end = datetime.now(timezone.utc)
        window_start = window_end - timedelta(days=365 * 5)  # 5-year window to cover historical ingest

        # Query all licitacao events in window
        stmt = select(Event).where(
            Event.type == "licitacao",
            Event.occurred_at >= window_start,
            Event.occurred_at <= window_end,
        )
        result = await session.execute(stmt)
        all_events = result.scalars().all()

        if not all_events:
            return []

        # Licitações sem adjudicação não têm alternativas reais — excluir
        _VOID = frozenset({"deserta", "fracassada", "revogada", "anulada", "cancelada"})

        # Separate inexigibilidade from competitive; filter out void situations
        inexigibilidade_events = [
            e for e in all_events
            if e.attrs.get("modality", "").lower() in _INEXIGIBILIDADE_MODALITIES
            and e.attrs.get("situacao", "").lower().strip() not in _VOID
        ]
        competitive_events = [
            e for e in all_events
            if e.attrs.get("modality", "").lower() in _COMPETITIVE_MODALITIES
        ]

        if not inexigibilidade_events:
            return []

        # Query participants for all events
        all_ids = [e.id for e in all_events]
        parts_stmt = select(EventParticipant).where(
            EventParticipant.event_id.in_(all_ids),
        )
        parts_result = await session.execute(parts_stmt)
        participants = parts_result.scalars().all()

        # Index participants by event
        event_roles: dict[str, dict[str, set]] = defaultdict(lambda: defaultdict(set))
        for p in participants:
            event_roles[str(p.event_id)][p.role].add(str(p.entity_id))

        # For competitive events: group by CATMAT → set of suppliers who competed.
        # Skip sentinel CATMAT values to avoid lumping all unclassified events.
        catmat_competitive_suppliers: dict[str, set] = defaultdict(set)
        for e in competitive_events:
            catmat = str(e.attrs.get("catmat_group") or e.attrs.get("catmat_code") or "")
            if catmat.strip().lower() in _CATMAT_MISSING:
                continue
            roles = event_roles.get(str(e.id), {})
            for supplier_id in (
                roles.get("winner", set())
                | roles.get("bidder", set())
                | roles.get("participant", set())
            ):
                catmat_competitive_suppliers[catmat].add(supplier_id)

        # For inexigibilidade: group by (agency, catmat) → events.
        # Skip sentinel CATMAT values for the same reason.
        inexig_groups: dict[tuple, list[Event]] = defaultdict(list)
        for e in inexigibilidade_events:
            catmat = str(e.attrs.get("catmat_group") or e.attrs.get("catmat_code") or "")
            if catmat.strip().lower() in _CATMAT_MISSING:
                continue
            buyers = event_roles.get(str(e.id), {}).get("buyer", set()) | \
                     event_roles.get(str(e.id), {}).get("procuring_entity", set())
            agency = next(iter(buyers), "unknown")
            inexig_groups[(agency, catmat)].append(e)

        signals: list[RiskSignalOut] = []

        for (agency_id, catmat), events_group in inexig_groups.items():
            n_alternatives = len(catmat_competitive_suppliers.get(catmat, set()))

            if n_alternatives < _MIN_ALTERNATIVE_SUPPLIERS:
                continue

            # Group by supplier to detect repeats
            supplier_events: dict[str, list[Event]] = defaultdict(list)
            for e in events_group:
                roles = event_roles.get(str(e.id), {})
                suppliers = roles.get("supplier", set()) | roles.get("winner", set())
                for s in suppliers:
                    supplier_events[s].append(e)

            for supplier_id, sup_events in supplier_events.items():
                n_repeat = len(sup_events)
                if n_repeat < _MIN_REPEAT_INEXIGIBILIDADE:
                    continue

                total_value = sum(e.value_brl or 0 for e in sup_events)

                if n_alternatives >= 5 and n_repeat >= 3:
                    severity = SignalSeverity.CRITICAL
                    confidence = min(0.88, 0.70 + n_alternatives * 0.03)
                elif n_alternatives >= 3 or n_repeat >= 2:
                    severity = SignalSeverity.HIGH
                    confidence = 0.68
                else:
                    severity = SignalSeverity.MEDIUM
                    confidence = 0.55

                first = min(sup_events, key=lambda e: e.occurred_at or datetime.min.replace(tzinfo=timezone.utc))
                last = max(sup_events, key=lambda e: e.occurred_at or datetime.min.replace(tzinfo=timezone.utc))

                entity_ids: list[uuid.UUID] = []
                for uid in [agency_id, supplier_id]:
                    if uid != "unknown":
                        try:
                            entity_ids.append(uuid.UUID(uid))
                        except ValueError:
                            pass

                signal = RiskSignalOut(
                    id=uuid.uuid4(),
                    typology_code=self.id,
                    typology_name=self.name,
                    severity=severity,
                    confidence=confidence,
                    title=(
                        f"Inexigibilidade suspeita — {n_alternatives} fornecedor(es) "
                        f"concorrente(s) existem no grupo CATMAT {catmat}"
                    ),
                    summary=(
                        f"Fornecedor recebeu {n_repeat} contrato(s) por inexigibilidade "
                        f"no grupo CATMAT {catmat}, onde {n_alternatives} fornecedor(es) "
                        f"concorrente(s) participaram de licitações competitivas similares. "
                        f"Valor total: R$ {total_value:,.2f}."
                    ),
                    factors={
                        "n_alternative_suppliers": n_alternatives,
                        "n_inexigibilidade_contracts": n_repeat,
                        "total_value_brl": round(total_value, 2),
                        "repeat_inexigibilidade": n_repeat >= _MIN_REPEAT_INEXIGIBILIDADE,
                        "catmat_group": catmat,
                    },
                    evidence_refs=[
                        EvidenceRef(
                            ref_type=RefType.EVENT,
                            ref_id=str(e.id),
                            description=(
                                f"Inexigibilidade R$ {e.value_brl:,.2f} "
                                f"em {e.occurred_at.strftime('%d/%m/%Y') if e.occurred_at else 'N/A'}"
                            ),
                        )
                        for e in sup_events[:5]
                    ],
                    entity_ids=entity_ids,
                    event_ids=[e.id for e in sup_events],
                    period_start=first.occurred_at,
                    period_end=last.occurred_at,
                    created_at=datetime.now(timezone.utc),
                )
                signals.append(signal)

        return signals
