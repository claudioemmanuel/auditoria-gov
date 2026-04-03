import uuid
from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy import select

from shared.models.orm import Event, EventParticipant
from shared.models.signals import (
    EvidenceRef,
    RefType,
    RiskSignalOut,
    SignalSeverity,
)
from shared.typologies.base import BaseTypology
from shared.utils.query import execute_chunked_in

_VOID = frozenset({"deserta", "fracassada", "revogada", "anulada", "cancelada"})


class T20PhantomBidderTypology(BaseTypology):
    """T20 — Licitante Fantasma (Phantom Bidder Detection).

    Detects companies that repeatedly participate in procurements but never win,
    always appearing alongside the same winning company (suggesting phantom
    participation to simulate competition).

    Algorithm:
    1. Query licitacao events in 5-year window.
    2. Build participation matrix: for each bidder, track events_participated and
       events_won.
    3. Filter candidates: win_rate == 0.0 AND participation_count >= 5.
    4. For each candidate, find their most frequent co-winner:
       - For each event the candidate participated in, find who won.
       - dominant_winner = winner that appears in >60% of their events.
    5. Signal if: participation_count >= 5 AND dominant_partner_win_rate >= 0.6.
    6. Severity: HIGH if participation_count >= 10, MEDIUM if 5-9.
    """

    @property
    def id(self) -> str:
        return "T20"

    @property
    def name(self) -> str:
        return "Licitante Fantasma"

    @property
    def required_domains(self) -> list[str]:
        return ["licitacao"]

    @property
    def required_fields(self) -> list[str]:
        return ["participants", "winner_entity_id"]

    @property
    def corruption_types(self) -> list[str]:
        return ["fraude_licitatoria"]

    @property
    def spheres(self) -> list[str]:
        return ["privada"]

    @property
    def evidence_level(self) -> str:
        return "indirect"

    async def run(self, session) -> list[RiskSignalOut]:
        window_start, window_end = await self.resolve_window(session, self.required_domains)

        stmt = select(Event).where(
            Event.type == "licitacao",
            Event.occurred_at >= window_start,
            Event.occurred_at <= window_end,
        )
        result = await session.execute(stmt)
        events = result.scalars().all()

        if len(events) < 5:
            return []

        event_ids = [e.id for e in events]

        participants = await execute_chunked_in(
            session,
            lambda batch: select(EventParticipant).where(
                EventParticipant.event_id.in_(batch),
            ),
            event_ids,
        )

        # Filter void events by building a valid event id set first
        valid_event_ids: set[str] = {
            str(e.id)
            for e in events
            if e.attrs.get("situacao", "").lower().strip() not in _VOID
        }

        # Build participation maps restricted to valid (non-void) events
        # bidder_events[entity_id] = set of event_ids they participated in
        # bidder_wins[entity_id] = set of event_ids they won
        # event_winners[event_id] = set of winner entity_ids
        bidder_events: dict[str, set[str]] = defaultdict(set)
        bidder_wins: dict[str, set[str]] = defaultdict(set)
        event_winners: dict[str, set[str]] = defaultdict(set)

        for p in participants:
            eid = str(p.event_id)
            if eid not in valid_event_ids:
                continue
            entity_id = str(p.entity_id)
            if p.role in ("bidder", "winner"):
                bidder_events[entity_id].add(eid)
            if p.role == "winner":
                bidder_wins[entity_id].add(eid)
                event_winners[eid].add(entity_id)

        signals: list[RiskSignalOut] = []

        for candidate_id, participated_events in bidder_events.items():
            participation_count = len(participated_events)
            if participation_count < 5:
                continue

            won_events = bidder_wins.get(candidate_id, set())
            if len(won_events) > 0:
                # Not a zero-win bidder
                continue

            # win_rate == 0.0: find co-winner distribution
            co_winner_counts: dict[str, int] = defaultdict(int)
            for eid in participated_events:
                for winner_id in event_winners.get(eid, set()):
                    if winner_id != candidate_id:
                        co_winner_counts[winner_id] += 1

            if not co_winner_counts:
                continue

            dominant_winner = max(co_winner_counts, key=lambda k: co_winner_counts[k])
            dominant_count = co_winner_counts[dominant_winner]
            dominant_partner_win_rate = dominant_count / participation_count

            if dominant_partner_win_rate < 0.6:
                continue

            # Collect co-participation event IDs (events where both appear)
            co_participation_events = [
                eid for eid in participated_events
                if dominant_winner in event_winners.get(eid, set())
            ]

            if participation_count >= 10:
                severity = SignalSeverity.HIGH
                confidence = 0.80
            else:
                severity = SignalSeverity.MEDIUM
                confidence = 0.68

            # Build entity_ids
            entity_ids_t20: list[uuid.UUID] = []
            for eid_str in [candidate_id, dominant_winner]:
                if eid_str not in ("sem classificacao", "unknown", ""):
                    try:
                        entity_ids_t20.append(uuid.UUID(eid_str))
                    except ValueError:
                        pass

            co_event_ids_sample = sorted(co_participation_events)[:5]

            signal = RiskSignalOut(
                id=uuid.uuid4(),
                typology_code=self.id,
                typology_name=self.name,
                severity=severity,
                confidence=confidence,
                title="Possível licitante fantasma detectado",
                summary=(
                    f"Empresa participou de {participation_count} licitações sem nenhuma vitória. "
                    f"Vencedor dominante em {dominant_partner_win_rate:.0%} dos casos: "
                    f"{dominant_winner}."
                ),
                factors={
                    "phantom_entity_id": candidate_id,
                    "dominant_winner_entity_id": dominant_winner,
                    "participation_count": participation_count,
                    "win_rate": 0.0,
                    "dominant_partner_win_rate": round(dominant_partner_win_rate, 4),
                    "co_participation_events": co_event_ids_sample,
                },
                evidence_refs=[
                    EvidenceRef(
                        ref_type=RefType.EVENT,
                        ref_id=eid,
                        description="Licitação com participação fantasma",
                    )
                    for eid in co_event_ids_sample
                ],
                entity_ids=entity_ids_t20,
                event_ids=[uuid.UUID(eid) for eid in co_event_ids_sample],
                period_start=window_start,
                period_end=window_end,
                created_at=datetime.now(timezone.utc),
            )
            signals.append(signal)

        return signals
