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
from shared.utils.query import execute_chunked_in

_VOID = frozenset({"deserta", "fracassada", "revogada", "anulada", "cancelada"})


class T19BidRotationTypology(BaseTypology):
    """T19 — Rodizio de Vencedores (Bid Rotation Detection).

    Detects procurement agencies where a small set of companies rotates winning
    over time (each wins in sequence, then repeats).

    Algorithm:
    1. Query licitacao events in 5-year window.
    2. Group by (buyer, catmat_group) — skip CATMAT_MISSING, void events.
    3. For groups with >= 4 procurements:
       a. Sort events by occurred_at.
       b. Compute rotation_entropy = n_unique_winners / n_procurements.
       c. Flag rotation if: 0.20 <= rotation_entropy <= 0.65 AND
          n_unique_winners >= 2 AND n_unique_winners <= 6.
       d. Check temporal pattern: winner at position i != winner at position i+1
          for at least 60% of consecutive pairs (rotation_alternation_rate).
    4. Severity: CRITICAL if entropy in [0.20, 0.65] AND alternation_rate >= 0.7
                            AND n_procs >= 6.
                HIGH if entropy in [0.20, 0.65] AND alternation_rate >= 0.5.
    """

    @property
    def id(self) -> str:
        return "T19"

    @property
    def name(self) -> str:
        return "Rodizio de Vencedores"

    @property
    def required_domains(self) -> list[str]:
        return ["licitacao"]

    @property
    def required_fields(self) -> list[str]:
        return ["participants", "winner_entity_id"]

    @property
    def corruption_types(self) -> list[str]:
        return ["fraude_licitatoria", "corrupcao_ativa"]

    @property
    def spheres(self) -> list[str]:
        return ["privada", "sistemica"]

    @property
    def evidence_level(self) -> str:
        return "indirect"

    async def run(self, session) -> list[RiskSignalOut]:
        window_end = datetime.now(timezone.utc)
        window_start = window_end - timedelta(days=365 * 5)

        stmt = select(Event).where(
            Event.type == "licitacao",
            Event.occurred_at >= window_start,
            Event.occurred_at <= window_end,
        )
        result = await session.execute(stmt)
        events = result.scalars().all()

        if len(events) < 4:
            return []

        event_ids = [e.id for e in events]

        participants = await execute_chunked_in(
            session,
            lambda batch: select(EventParticipant).where(
                EventParticipant.event_id.in_(batch),
            ),
            event_ids,
        )

        event_winners: dict[str, list[str]] = defaultdict(list)
        event_buyers: dict[str, str] = {}

        for p in participants:
            eid = str(p.event_id)
            entity_id = str(p.entity_id)
            if p.role == "winner":
                event_winners[eid].append(entity_id)
            elif p.role in ("procuring_entity", "buyer"):
                event_buyers[eid] = entity_id

        # Filter void events
        events = [
            e for e in events
            if e.attrs.get("situacao", "").lower().strip() not in _VOID
        ]

        if len(events) < 4:
            return []

        # Group events by (buyer, catmat_group); skip CATMAT_MISSING sentinel
        groups: dict[tuple, list[Event]] = defaultdict(list)
        for e in events:
            eid = str(e.id)
            catmat_raw = e.attrs.get("catmat_group", "") or ""
            if str(catmat_raw).strip().lower() in _CATMAT_MISSING:
                continue
            buyer = event_buyers.get(eid, "unknown")
            groups[(buyer, catmat_raw)].append(e)

        signals: list[RiskSignalOut] = []

        for key, group_events in groups.items():
            buyer_id_str, catmat = key
            n_procs = len(group_events)
            if n_procs < 4:
                continue

            # Sort by occurred_at for temporal analysis
            group_events_sorted = sorted(group_events, key=lambda e: e.occurred_at)

            # Build ordered winner sequence (first winner per event)
            winner_sequence: list[str] = []
            for e in group_events_sorted:
                eid = str(e.id)
                winners = event_winners.get(eid, [])
                winner_sequence.append(winners[0] if winners else "")

            all_unique_winners = {w for w in winner_sequence if w}
            n_unique_winners = len(all_unique_winners)

            if n_unique_winners < 2 or n_unique_winners > 6:
                continue

            rotation_entropy = n_unique_winners / n_procs

            if not (0.20 <= rotation_entropy <= 0.65):
                continue

            # Compute rotation_alternation_rate: fraction of consecutive pairs
            # where winner changes
            consecutive_pairs = [
                (winner_sequence[i], winner_sequence[i + 1])
                for i in range(len(winner_sequence) - 1)
                if winner_sequence[i] and winner_sequence[i + 1]
            ]
            if not consecutive_pairs:
                continue

            alternating_pairs = sum(
                1 for a, b in consecutive_pairs if a != b
            )
            rotation_alternation_rate = alternating_pairs / len(consecutive_pairs)

            if rotation_alternation_rate < 0.5:
                continue

            # Determine severity
            if (
                rotation_alternation_rate >= 0.7
                and n_procs >= 6
            ):
                severity = SignalSeverity.CRITICAL
                confidence = 0.88
            else:
                severity = SignalSeverity.HIGH
                confidence = 0.72

            # Build entity_ids: buyer + unique winners
            entity_ids_t19: list[uuid.UUID] = []
            if buyer_id_str not in ("sem classificacao", "unknown"):
                try:
                    entity_ids_t19.append(uuid.UUID(buyer_id_str))
                except ValueError:
                    pass
            for w in list(all_unique_winners)[:9]:
                if w not in ("sem classificacao", "unknown", ""):
                    try:
                        entity_ids_t19.append(uuid.UUID(w))
                    except ValueError:
                        pass

            group_event_ids = [str(e.id) for e in group_events_sorted]

            signal = RiskSignalOut(
                id=uuid.uuid4(),
                typology_code=self.id,
                typology_name=self.name,
                severity=severity,
                confidence=confidence,
                title=f"Possível rodízio de vencedores — {catmat}",
                summary=(
                    f"Padrão de rodízio detectado em {n_procs} licitações. "
                    f"Entropia de rotação: {rotation_entropy:.2f} "
                    f"({n_unique_winners} vencedores únicos). "
                    f"Taxa de alternância: {rotation_alternation_rate:.2f}."
                ),
                factors={
                    "n_procurements": n_procs,
                    "n_unique_winners": n_unique_winners,
                    "rotation_entropy": round(rotation_entropy, 4),
                    "rotation_alternation_rate": round(rotation_alternation_rate, 4),
                    "catmat_group": catmat,
                    "winner_sequence": winner_sequence[:10],
                },
                evidence_refs=[
                    EvidenceRef(
                        ref_type=RefType.EVENT,
                        ref_id=eid,
                        description="Licitação do grupo com rodízio",
                    )
                    for eid in group_event_ids[:5]
                ],
                entity_ids=entity_ids_t19,
                event_ids=[uuid.UUID(eid) for eid in group_event_ids[:20]],
                period_start=window_start,
                period_end=window_end,
                created_at=datetime.now(timezone.utc),
            )
            signals.append(signal)

        return signals
