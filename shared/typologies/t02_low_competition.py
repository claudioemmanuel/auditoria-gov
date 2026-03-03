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


class T02LowCompetitionTypology(BaseTypology):
    """T02 — Low Competition.

    Algorithm:
    1. For each procurement in the analysis window:
       a. Count distinct participants (bidders).
       b. Compare against BASELINE (PARTICIPANTS_PER_PROCUREMENT for same
          modality + CATMAT/CATSER group).
    2. Flag if n_participants < baseline p10.
    3. Severity: HIGH if n_participants <= 1, MEDIUM if < p10.
    """

    @property
    def id(self) -> str:
        return "T02"

    @property
    def name(self) -> str:
        return "Baixa Competição"

    @property
    def required_domains(self) -> list[str]:
        return ["licitacao"]

    @property
    def required_fields(self) -> list[str]:
        return ["n_participants", "modality"]

    async def run(self, session) -> list[RiskSignalOut]:
        window_end = datetime.now(timezone.utc)
        window_start = window_end - timedelta(days=365)

        # Query licitacao events
        stmt = (
            select(Event)
            .where(
                Event.type == "licitacao",
                Event.occurred_at >= window_start,
                Event.occurred_at <= window_end,
            )
        )
        result = await session.execute(stmt)
        events = result.scalars().all()

        if not events:
            return []

        event_ids = [e.id for e in events]

        # Count bidders per event
        bidder_stmt = select(EventParticipant).where(
            EventParticipant.event_id.in_(event_ids),
            EventParticipant.role == "bidder",
        )
        bidder_result = await session.execute(bidder_stmt)
        bidders = bidder_result.scalars().all()

        # Group bidders by event
        bidder_counts: dict[str, set[str]] = defaultdict(set)
        for b in bidders:
            bidder_counts[str(b.event_id)].add(str(b.entity_id))

        # Build event info map
        event_info: dict[str, dict] = {}
        for e in events:
            event_info[str(e.id)] = {
                "modality": e.attrs.get("modality", "nao informada"),
                "description": e.description,
                "value_brl": e.value_brl,
                "occurred_at": e.occurred_at,
            }

        # Get baseline
        baseline = await get_baseline(
            session,
            BaselineType.PARTICIPANTS_PER_PROCUREMENT.value,
            "national::all",
        )
        p10 = baseline.get("p10", 3.0) if baseline else 3.0

        signals: list[RiskSignalOut] = []

        for e in events:
            eid = str(e.id)
            n_bidders = len(bidder_counts.get(eid, set()))
            info = event_info[eid]

            if n_bidders >= p10:
                continue

            # Determine severity
            if n_bidders <= 1:
                severity = SignalSeverity.HIGH
                confidence = 0.90
            else:
                severity = SignalSeverity.MEDIUM
                confidence = min(0.85, 0.5 + (p10 - n_bidders) / p10 * 0.4)

            value_str = f"R$ {info['value_brl']:,.2f}" if info["value_brl"] else "N/A"

            signal = RiskSignalOut(
                id=uuid.uuid4(),
                typology_code=self.id,
                typology_name=self.name,
                severity=severity,
                confidence=confidence,
                title=f"Baixa competição — {n_bidders} participante(s)",
                summary=(
                    f"Licitação com apenas {n_bidders} participante(s), "
                    f"abaixo do p10 do baseline ({p10:.1f}). "
                    f"Modalidade: {info['modality']}. Valor: {value_str}."
                ),
                factors={
                    "n_bidders": n_bidders,
                    "baseline_p10": round(p10, 2),
                    "modality": info["modality"],
                    "value_brl": info["value_brl"],
                },
                evidence_refs=[
                    EvidenceRef(
                        ref_type=RefType.EVENT,
                        ref_id=eid,
                        description=f"Licitação com {n_bidders} participante(s)",
                    ),
                    EvidenceRef(
                        ref_type=RefType.BASELINE,
                        description=f"Baseline p10 = {p10:.1f} participantes",
                    ),
                ],
                entity_ids=[],
                event_ids=[e.id],
                period_start=window_start,
                period_end=window_end,
                created_at=datetime.now(timezone.utc),
            )
            signals.append(signal)

        return signals
