import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from shared.models.orm import Event, EventParticipant
from shared.models.signals import (
    EvidenceRef,
    RefType,
    RiskSignalOut,
    SignalSeverity,
)
from shared.typologies.base import BaseTypology


class T07CartelNetworkTypology(BaseTypology):
    """T07 — Cartel Network Detection.

    Algorithm:
    1. Winner alternation: for a procuring entity + object group,
       detect if the same small set of companies take turns winning.
       Metric: n_unique_winners / n_procurements < threshold (0.3).
    2. Co-participation density: companies that always bid together
       but rarely win against each other → suspicious coordination.
    3. Community detection: run Louvain on the co-bidding graph.
       Flag tightly-connected communities with alternating winners.
    4. Severity: CRITICAL if all 3 factors present, HIGH if 2.
    """

    @property
    def id(self) -> str:
        return "T07"

    @property
    def name(self) -> str:
        return "Rede de Cartel"

    @property
    def required_domains(self) -> list[str]:
        return ["licitacao"]

    @property
    def required_fields(self) -> list[str]:
        return ["participants", "winner_entity_id"]

    async def run(self, session) -> list[RiskSignalOut]:
        window_end = datetime.now(timezone.utc)
        window_start = window_end - timedelta(days=365 * 2)

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

        if len(events) < 3:
            return []

        event_ids = [e.id for e in events]
        event_map: dict[str, Event] = {str(e.id): e for e in events}

        # Get all participants
        part_stmt = select(EventParticipant).where(
            EventParticipant.event_id.in_(event_ids),
        )
        part_result = await session.execute(part_stmt)
        participants = part_result.scalars().all()

        # Group by event
        event_bidders: dict[str, set[str]] = defaultdict(set)
        event_winners: dict[str, set[str]] = defaultdict(set)
        event_buyers: dict[str, str] = {}

        for p in participants:
            eid = str(p.event_id)
            entity_id = str(p.entity_id)
            if p.role == "bidder":
                event_bidders[eid].add(entity_id)
            elif p.role == "winner":
                event_winners[eid].add(entity_id)
                event_bidders[eid].add(entity_id)  # Winners are also bidders
            elif p.role in ("procuring_entity", "buyer"):
                event_buyers[eid] = entity_id

        # Group events by (buyer, catmat_group)
        groups: dict[tuple, list[str]] = defaultdict(list)
        for e in events:
            eid = str(e.id)
            buyer = event_buyers.get(eid, "sem classificacao")
            catmat = e.attrs.get("catmat_group", "sem classificacao")
            groups[(buyer, catmat)].append(eid)

        signals: list[RiskSignalOut] = []

        for key, group_event_ids in groups.items():
            buyer_id_str, catmat = key
            n_procs = len(group_event_ids)
            if n_procs < 3:
                continue

            # 1. Winner alternation metric
            all_winners: set[str] = set()
            for eid in group_event_ids:
                all_winners |= event_winners.get(eid, set())

            n_unique_winners = len(all_winners)
            alternation_ratio = n_unique_winners / n_procs if n_procs > 0 else 1.0

            alternation_flag = alternation_ratio < 0.3 and n_unique_winners >= 2

            # 2. Co-participation density
            # Build co-bidding matrix: how often pairs of bidders appear together
            pair_counts: dict[tuple, int] = defaultdict(int)
            all_bidders: set[str] = set()
            for eid in group_event_ids:
                bidders = sorted(event_bidders.get(eid, set()))
                all_bidders |= set(bidders)
                for i in range(len(bidders)):
                    for j in range(i + 1, len(bidders)):
                        pair = (bidders[i], bidders[j])
                        pair_counts[pair] += 1

            # High co-participation: pairs that appear together in >50% of procurements
            high_copart_pairs = [
                (a, b, cnt) for (a, b), cnt in pair_counts.items()
                if cnt >= n_procs * 0.5
            ]
            copart_flag = len(high_copart_pairs) >= 1

            # 3. Community detection via simple connected components
            # (Louvain requires networkx — use it if available, otherwise fallback)
            communities: list[set[str]] = []
            try:
                import networkx as nx
                G = nx.Graph()
                for (a, b), cnt in pair_counts.items():
                    if cnt >= 2:
                        G.add_edge(a, b, weight=cnt)

                if G.number_of_nodes() >= 3:
                    louvain_comms = nx.community.louvain_communities(G, seed=42)
                    communities = [c for c in louvain_comms if len(c) >= 3]
            except ImportError:
                # Fallback: simple connected component detection
                if high_copart_pairs:
                    connected: set[str] = set()
                    for a, b, _ in high_copart_pairs:
                        connected.add(a)
                        connected.add(b)
                    if len(connected) >= 3:
                        communities = [connected]

            community_flag = len(communities) >= 1

            # Count flagged factors
            n_factors = sum([alternation_flag, copart_flag, community_flag])
            if n_factors < 2:
                continue

            if n_factors >= 3:
                severity = SignalSeverity.CRITICAL
                confidence = 0.90
            else:
                severity = SignalSeverity.HIGH
                confidence = 0.75

            community_members = list(communities[0])[:10] if communities else list(all_winners)[:10]

            signal = RiskSignalOut(
                id=uuid.uuid4(),
                typology_code=self.id,
                typology_name=self.name,
                severity=severity,
                confidence=confidence,
                title=f"Possível cartel — {catmat}",
                summary=(
                    f"Padrão de cartel detectado em {n_procs} licitações. "
                    f"Alternância de vencedores: {alternation_ratio:.2f} "
                    f"({n_unique_winners} vencedores únicos). "
                    f"Co-participação elevada: {len(high_copart_pairs)} par(es). "
                    f"Comunidades detectadas: {len(communities)}."
                ),
                factors={
                    "n_procurements": n_procs,
                    "n_unique_winners": n_unique_winners,
                    "alternation_ratio": round(alternation_ratio, 4),
                    "alternation_flag": alternation_flag,
                    "high_copart_pairs": len(high_copart_pairs),
                    "copart_flag": copart_flag,
                    "n_communities": len(communities),
                    "community_flag": community_flag,
                    "n_factors": n_factors,
                    "catmat_group": catmat,
                    "community_members": community_members,
                },
                evidence_refs=[
                    EvidenceRef(
                        ref_type=RefType.EVENT,
                        ref_id=eid,
                        description=f"Licitação do grupo",
                    )
                    for eid in group_event_ids[:5]
                ],
                entity_ids=[
                    uuid.UUID(eid) for eid in community_members[:10]
                    if eid != "sem classificacao"
                ],
                event_ids=[uuid.UUID(eid) for eid in group_event_ids[:20]],
                period_start=window_start,
                period_end=window_end,
                created_at=datetime.now(timezone.utc),
            )
            signals.append(signal)

        return signals
