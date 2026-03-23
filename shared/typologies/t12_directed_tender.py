import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from shared.baselines.compute import _CATMAT_MISSING
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

# Maximum number of bidders to consider "suspiciously restricted"
_MAX_BIDDERS_THRESHOLD = 2
# Minimum repetitions of the same winner at the same agency to trigger "repeat winner"
_MIN_REPEAT_WINS = 3


class T12DirectedTenderTypology(BaseTypology):
    """T12 — Edital Direcionado (Restricted Competitive Tender).

    Algorithm:
    1. For each procuring entity + CATMAT group:
       a. Find competitive licitacoes (not inexigibilidade/dispensa).
       b. Identify processes with n_bidders ≤ 2 (below baseline p10).
    2. Among low-bidder processes, detect repeat winner patterns:
       same supplier winning ≥ 3 times at the same agency.
    3. Flag agency-supplier pairs where both conditions hold:
       persistent low competition AND concentration in same winner.
    4. Severity: CRITICAL if n_bidders = 1 AND repeat_wins ≥ 5; HIGH otherwise.

    Legal basis:
    - Lei 14.133/2021, Art. 9°, IV (conflict of interest; bidder disqualification)
    - Lei 8.666/93, Art. 3°, § 1° (clauses restricting competitive character)
    - Lei 8.429/92, Art. 10, VIII (frustrating competitive procurement)
    - TCU Fiscobras: "Restriction on Competitive Character" (498 occurrences)
    """

    @property
    def id(self) -> str:
        return "T12"

    @property
    def name(self) -> str:
        return "Edital Direcionado"

    @property
    def required_domains(self) -> list[str]:
        return ["licitacao"]

    @property
    def required_fields(self) -> list[str]:
        return ["modality", "catmat_group"]

    @property
    def corruption_types(self) -> list[str]:
        return ["fraude_licitatoria", "corrupcao_ativa_passiva"]

    @property
    def spheres(self) -> list[str]:
        return ["administrativa"]

    @property
    def evidence_level(self) -> str:
        return "indirect"

    async def run(self, session) -> list[RiskSignalOut]:
        window_end = datetime.now(timezone.utc)
        window_start = window_end - timedelta(days=365 * 5)  # 5-year window to cover historical ingest

        # Query competitive procurement events (exclude sole-source/dispensa)
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

        # Licitações sem adjudicação não têm vencedor real — excluir antes da análise
        _VOID = frozenset({"deserta", "fracassada", "revogada", "anulada", "cancelada"})

        # Filter to competitive modalities only, excluding void situations
        competitive = [
            e for e in events
            if e.attrs.get("modality", "").lower() not in (
                "inexigibilidade", "dispensa", "dispensa_licitacao",
                "dispensa_valor", "dispensa de licitacao",
            )
            and e.attrs.get("situacao", "").lower().strip() not in _VOID
        ]

        if not competitive:
            return []

        event_ids = [e.id for e in competitive]
        participants = await execute_chunked_in(
            session,
            lambda batch: select(EventParticipant).where(
                EventParticipant.event_id.in_(batch),
            ),
            event_ids,
        )

        # Build indexes
        event_bidders: dict[str, set] = defaultdict(set)
        event_winners: dict[str, set] = defaultdict(set)
        event_buyers: dict[str, set] = defaultdict(set)

        for p in participants:
            eid = str(p.event_id)
            if p.role in ("bidder", "participant"):
                event_bidders[eid].add(p.entity_id)
            elif p.role == "winner":
                event_winners[eid].add(p.entity_id)
            elif p.role in ("buyer", "procuring_entity"):
                event_buyers[eid].add(p.entity_id)

        # Get participants baseline
        baseline = await get_baseline(
            session,
            BaselineType.PARTICIPANTS_PER_PROCUREMENT.value,
            "national::all",
        )
        p10 = baseline.get("p10", 3.0) if baseline else 3.0

        # Group: (buyer, catmat_group) → events; skip sentinel CATMAT to avoid
        # lumping all unclassified events into one spurious directed-tender group.
        groups: dict[tuple, list[Event]] = defaultdict(list)
        for e in competitive:
            catmat = str(e.attrs.get("catmat_group") or "")
            if catmat.strip().lower() in _CATMAT_MISSING:
                continue
            buyers = event_buyers.get(str(e.id), set())
            buyer_id = next(iter(buyers), "unknown")
            groups[(str(buyer_id), catmat)].append(e)

        signals: list[RiskSignalOut] = []

        for (buyer_id_str, catmat), group_events in groups.items():
            if len(group_events) < _MIN_REPEAT_WINS:
                continue

            # Count bidder counts and winner frequencies
            low_bidder_events = []
            winner_freq: dict[str, int] = defaultdict(int)
            winner_event_ids: dict[str, list] = defaultdict(list)

            for e in group_events:
                eid = str(e.id)
                n_bidders = len(event_bidders.get(eid, set()))
                winners = event_winners.get(eid, set())

                if n_bidders <= max(p10, _MAX_BIDDERS_THRESHOLD) or n_bidders == 0:
                    low_bidder_events.append(e)

                for w in winners:
                    winner_freq[str(w)] += 1
                    winner_event_ids[str(w)].append(e.id)

            if not low_bidder_events:
                continue

            # Find repeat winners
            repeat_winners = {
                wid: count for wid, count in winner_freq.items()
                if count >= _MIN_REPEAT_WINS
            }
            if not repeat_winners:
                continue

            for winner_id_str, win_count in repeat_winners.items():
                winner_events = winner_event_ids[winner_id_str]
                low_bidder_win_events = [
                    e for e in low_bidder_events
                    if e.id in winner_events
                ]

                if len(low_bidder_win_events) < _MIN_REPEAT_WINS:
                    continue

                # Compute restrictiveness score
                avg_bidders = sum(
                    len(event_bidders.get(str(e.id), set())) or 1
                    for e in low_bidder_win_events
                ) / len(low_bidder_win_events)

                pct_single_bidder = sum(
                    1 for e in low_bidder_win_events
                    if len(event_bidders.get(str(e.id), set())) <= 1
                ) / len(low_bidder_win_events)

                restrictiveness_score = min(1.0, (1.0 - avg_bidders / 10) * 0.6 + pct_single_bidder * 0.4)

                # PMI attenuation: a prior PMI increases legitimate market exposure,
                # so the restrictiveness score is halved when pmi_realizado=True on
                # the majority of the events in this group.
                pmi_count = sum(
                    1 for e in low_bidder_win_events
                    if (e.attrs or {}).get("pmi_realizado") is True
                )
                pmi_majority = pmi_count > len(low_bidder_win_events) / 2
                if pmi_majority:
                    restrictiveness_score *= 0.5

                if pct_single_bidder >= 0.5 and win_count >= 5:
                    severity = SignalSeverity.CRITICAL
                    confidence = min(0.90, 0.75 + win_count * 0.02)
                elif restrictiveness_score >= 0.5:
                    severity = SignalSeverity.HIGH
                    confidence = min(0.80, 0.60 + restrictiveness_score * 0.2)
                else:
                    severity = SignalSeverity.MEDIUM
                    confidence = 0.55

                all_event_ids = winner_event_ids[winner_id_str]
                first_event = min(
                    (e for e in group_events if e.id in all_event_ids),
                    key=lambda e: e.occurred_at or datetime.min.replace(tzinfo=timezone.utc),
                    default=None,
                )
                last_event = max(
                    (e for e in group_events if e.id in all_event_ids),
                    key=lambda e: e.occurred_at or datetime.min.replace(tzinfo=timezone.utc),
                    default=None,
                )

                entity_ids = []
                if buyer_id_str != "unknown":
                    try:
                        entity_ids.append(uuid.UUID(buyer_id_str))
                    except ValueError:
                        pass
                try:
                    entity_ids.append(uuid.UUID(winner_id_str))
                except ValueError:
                    pass

                signal = RiskSignalOut(
                    id=uuid.uuid4(),
                    typology_code=self.id,
                    typology_name=self.name,
                    severity=severity,
                    confidence=confidence,
                    title=(
                        f"Edital direcionado — fornecedor venceu {win_count}× "
                        f"com baixa competição (CATMAT: {catmat})"
                    ),
                    summary=(
                        f"Mesmo fornecedor venceu {win_count} licitação(ões) "
                        f"no grupo CATMAT {catmat} com média de {avg_bidders:.1f} "
                        f"licitante(s) por processo. "
                        f"{pct_single_bidder:.0%} dos processos tiveram apenas 1 participante. "
                        f"Score de restrição: {restrictiveness_score:.2f}."
                    ),
                    factors={
                        "n_bidders": round(avg_bidders, 1),
                        "restrictiveness_score": round(restrictiveness_score, 3),
                        "repeat_winner": True,
                        "single_eligible": pct_single_bidder >= 0.5,
                        "win_count": win_count,
                        "n_low_bidder_events": len(low_bidder_win_events),
                        "pct_single_bidder": round(pct_single_bidder, 3),
                        "catmat_group": catmat,
                        "baseline_p10": round(p10, 1),
                        "pmi_realizado": pmi_majority,
                    },
                    evidence_refs=[
                        EvidenceRef(
                            ref_type=RefType.EVENT,
                            ref_id=str(e.id),
                            description=(
                                f"Licitação com {len(event_bidders.get(str(e.id), set()))} licitante(s) "
                                f"em {e.occurred_at.strftime('%d/%m/%Y') if e.occurred_at else 'N/A'}"
                            ),
                        )
                        for e in low_bidder_win_events[:5]
                    ],
                    entity_ids=entity_ids,
                    event_ids=all_event_ids[:20],
                    period_start=first_event.occurred_at if first_event else None,
                    period_end=last_event.occurred_at if last_event else window_end,
                    created_at=datetime.now(timezone.utc),
                )
                signals.append(signal)

        return signals
