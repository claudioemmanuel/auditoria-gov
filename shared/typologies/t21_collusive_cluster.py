import uuid
from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy import select

from shared.baselines.compute import _CATMAT_MISSING
from shared.models.orm import Event, EventParticipant, RiskSignal, Typology
from shared.models.signals import (
    EvidenceRef,
    RefType,
    RiskSignalOut,
    SignalSeverity,
)
from shared.typologies.base import BaseTypology
from shared.utils.query import execute_chunked_in


class T21CollusiveClusterTypology(BaseTypology):
    """T21 — Cluster Colusivo.

    Algorithm:
    1. Query licitacao events in 5-year window.
    2. Build co-bidding graph: companies are nodes, edge weight = number of
       times they co-participated.
    3. Run Louvain community detection (networkx) — same try/except as T07.
    4. For each community with >= 3 members:
       a. Get all procurements where community members participated.
       b. Compute intra_cluster_win_rate = wins_by_community_members /
          total_wins_in_those_procurements.
       c. Flag if: intra_cluster_win_rate >= 0.80 AND
          total_procurements_in_community_scope >= 5.
    5. Deduplicate vs T07: skip communities whose members are a SUBSET of any
       existing T07 signal's entity_ids.
    6. Severity: CRITICAL if cluster_size >= 5 AND win_rate >= 0.90,
                 HIGH if cluster_size >= 3 AND win_rate >= 0.80.
    """

    @property
    def id(self) -> str:
        return "T21"

    @property
    def name(self) -> str:
        return "Cluster Colusivo"

    @property
    def required_domains(self) -> list[str]:
        return ["licitacao"]

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
        window_start, window_end = await self.resolve_window(session, self.required_domains)

        # Query licitacao events
        stmt = select(Event).where(
            Event.type == "licitacao",
            Event.occurred_at >= window_start,
            Event.occurred_at <= window_end,
        )
        result = await session.execute(stmt)
        events = result.scalars().all()

        if len(events) < 3:
            return []

        event_ids = [e.id for e in events]

        # Get all participants
        participants = await execute_chunked_in(
            session,
            lambda batch: select(EventParticipant).where(
                EventParticipant.event_id.in_(batch),
            ),
            event_ids,
        )

        # Group by event
        event_bidders: dict[str, set[str]] = defaultdict(set)
        event_winners: dict[str, set[str]] = defaultdict(set)

        for p in participants:
            eid = str(p.event_id)
            entity_id = str(p.entity_id)
            if p.role == "bidder":
                event_bidders[eid].add(entity_id)
            elif p.role == "winner":
                event_winners[eid].add(entity_id)
                event_bidders[eid].add(entity_id)  # Winners are also bidders

        # Skip void events
        _VOID = frozenset({"deserta", "fracassada", "revogada", "anulada", "cancelada"})
        events = [
            e for e in events
            if e.attrs.get("situacao", "").lower().strip() not in _VOID
        ]

        if len(events) < 3:
            return []

        # Skip events with missing catmat to avoid spurious clusters
        valid_event_ids = set()
        for e in events:
            catmat_raw = e.attrs.get("catmat_group", "") or ""
            if str(catmat_raw).strip().lower() not in _CATMAT_MISSING:
                valid_event_ids.add(str(e.id))

        if len(valid_event_ids) < 3:
            return []

        # Build co-bidding graph across ALL valid events
        pair_counts: dict[tuple, int] = defaultdict(int)
        for eid in valid_event_ids:
            bidders = sorted(event_bidders.get(eid, set()))
            for i in range(len(bidders)):
                for j in range(i + 1, len(bidders)):
                    pair = (bidders[i], bidders[j])
                    pair_counts[pair] += 1

        # Community detection via Louvain (networkx) or fallback
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
            # Fallback: connected components from high co-participation pairs
            high_pairs = [(a, b) for (a, b), cnt in pair_counts.items() if cnt >= 2]
            if high_pairs:
                adj: dict[str, set[str]] = defaultdict(set)
                for a, b in high_pairs:
                    adj[a].add(b)
                    adj[b].add(a)
                visited: set[str] = set()
                for node in adj:
                    if node in visited:
                        continue
                    component: set[str] = set()
                    stack = [node]
                    while stack:
                        n = stack.pop()
                        if n in visited:
                            continue
                        visited.add(n)
                        component.add(n)
                        stack.extend(adj[n] - visited)
                    if len(component) >= 3:
                        communities.append(component)

        if not communities:
            return []

        # Load existing T07 signals to deduplicate
        t07_entity_sets: list[set[str]] = []
        try:
            t07_stmt = (
                select(RiskSignal)
                .join(Typology, RiskSignal.typology_id == Typology.id)
                .where(Typology.code == "T07")
            )
            t07_result = await session.execute(t07_stmt)
            t07_signals = t07_result.scalars().all()
            for sig in t07_signals:
                if sig.entity_ids:
                    t07_entity_sets.append({str(eid) for eid in sig.entity_ids})
        except Exception:
            # If ORM join fails (e.g. in tests with minimal mocks), skip dedup
            pass

        signals: list[RiskSignalOut] = []

        for community in communities:
            cluster_size = len(community)

            # Deduplicate: skip if community members are a subset of any T07 signal
            if t07_entity_sets:
                if any(community <= t07_set for t07_set in t07_entity_sets):
                    continue

            # Find all procurements where community members participated
            community_event_ids = [
                eid for eid in valid_event_ids
                if event_bidders.get(eid, set()) & community
            ]

            n_procurements = len(community_event_ids)
            if n_procurements < 5:
                continue

            # Compute intra-cluster win rate
            total_wins = 0
            community_wins = 0
            for eid in community_event_ids:
                winners = event_winners.get(eid, set())
                if winners:
                    total_wins += 1
                    if winners & community:
                        community_wins += 1

            if total_wins == 0:
                continue

            intra_cluster_win_rate = community_wins / total_wins

            if intra_cluster_win_rate < 0.80:
                continue

            # Severity
            if cluster_size >= 5 and intra_cluster_win_rate >= 0.90:
                severity = SignalSeverity.CRITICAL
                confidence = 0.88
            else:
                severity = SignalSeverity.HIGH
                confidence = 0.74

            member_entity_ids_str = sorted(community)[:10]
            entity_ids: list[uuid.UUID] = []
            for eid_str in member_entity_ids_str:
                try:
                    entity_ids.append(uuid.UUID(eid_str))
                except ValueError:
                    pass

            signal = RiskSignalOut(
                id=uuid.uuid4(),
                typology_code=self.id,
                typology_name=self.name,
                severity=severity,
                confidence=confidence,
                title=f"Cluster colusivo — {cluster_size} empresas, taxa de vitória {intra_cluster_win_rate:.0%}",
                summary=(
                    f"Comunidade de {cluster_size} empresas detectada com "
                    f"taxa de vitória interna de {intra_cluster_win_rate:.1%} "
                    f"em {n_procurements} licitações do escopo."
                ),
                factors={
                    "cluster_size": cluster_size,
                    "intra_cluster_win_rate": round(intra_cluster_win_rate, 4),
                    "n_procurements": n_procurements,
                    "community_wins": community_wins,
                    "total_wins": total_wins,
                    "member_entity_ids": member_entity_ids_str,
                },
                evidence_refs=[
                    EvidenceRef(
                        ref_type=RefType.EVENT,
                        ref_id=eid,
                        description="Licitação no escopo do cluster",
                    )
                    for eid in community_event_ids[:5]
                ],
                entity_ids=entity_ids,
                event_ids=[uuid.UUID(eid) for eid in community_event_ids[:20] if _is_uuid(eid)],
                period_start=window_start,
                period_end=window_end,
                created_at=datetime.now(timezone.utc),
            )
            signals.append(signal)

        return signals


def _is_uuid(s: str) -> bool:
    try:
        uuid.UUID(s)
        return True
    except ValueError:
        return False
