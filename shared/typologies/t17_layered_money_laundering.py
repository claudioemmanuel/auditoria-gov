import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from shared.models.orm import Event, EventParticipant, GraphEdge, GraphNode
from shared.models.signals import (
    EvidenceRef,
    RefType,
    RiskSignalOut,
    SignalSeverity,
)
from shared.typologies.base import BaseTypology

# Graph edge types that indicate corporate ownership/control links.
# Only includes types actively produced by shared/er/corporate_edges.py.
_OWNERSHIP_EDGE_TYPES = {
    "SAME_SOCIO",
    "SUBSIDIARY",
    "HOLDING",
}

# Maximum hops to detect a cycle
_MAX_CYCLE_HOPS = 3

# Minimum intra-community contract value to flag
_MIN_INTRA_COMMUNITY_VALUE = 50_000.0


def _find_cycles(
    graph: dict[str, set[str]],
    start: str,
    max_hops: int,
) -> list[list[str]]:
    """BFS to find cycles from start node within max_hops.

    Returns list of paths that form cycles (end == start).
    """
    cycles: list[list[str]] = []
    # queue: (current_node, path_so_far)
    queue = [(start, [start])]

    while queue:
        current, path = queue.pop(0)
        if len(path) > max_hops + 1:
            continue

        for neighbor in graph.get(current, set()):
            if neighbor == start and len(path) >= 2:
                # Require at least 2 distinct nodes before closing.  With a
                # directed graph, A→B→A only forms when there are explicit
                # back-edges in the data — a genuine circular ownership loop.
                cycles.append(path + [start])
                continue
            if neighbor not in path:
                queue.append((neighbor, path + [neighbor]))

    return cycles


class T17LayeredMoneyLaunderingTypology(BaseTypology):
    """T17 — Lavagem via Camadas Societárias e Fluxo Circular.

    Algorithm:
    1. Load ownership graph edges (SAME_SOCIO, SUBSIDIARY, HOLDING, etc.)
       from GraphEdge table.
    2. Resolve entity_ids via GraphNode.
    3. Build directed adjacency graph: entity → set of related entities.
    4. For each contract winner (from recent Events):
       a. Run BFS from winner's entity to detect cycles within ≤ 3 hops.
       b. A cycle indicates funds can flow back to the original UBO.
    5. Check if community members also appear as subcontractors in the
       same contract (intra-community transfer).
    6. Flag if cycle detected AND intra_community_value > R$ 50k.

    Legal basis:
    - Lei 9.613/1998, Art. 1° (money laundering)
    - FATF Recommendation 24 (ultimate beneficial owner / UBO transparency)
    - FATF Recommendation 3 (procurement as predicate offense for money laundering)
    """

    @property
    def id(self) -> str:
        return "T17"

    @property
    def name(self) -> str:
        return "Lavagem via Camadas Societárias"

    @property
    def required_domains(self) -> list[str]:
        return ["empresa", "contrato"]

    @property
    def required_fields(self) -> list[str]:
        return ["graph_edges"]

    @property
    def corruption_types(self) -> list[str]:
        return ["lavagem"]

    @property
    def spheres(self) -> list[str]:
        return ["privada", "sistemica"]

    @property
    def evidence_level(self) -> str:
        return "indirect"

    async def run(self, session) -> list[RiskSignalOut]:
        window_end = datetime.now(timezone.utc)
        window_start = window_end - timedelta(days=365 * 5)  # 5-year window to cover historical ingest

        # Load ownership/corporate graph edges
        edges_stmt = select(GraphEdge).where(
            GraphEdge.type.in_(_OWNERSHIP_EDGE_TYPES),
        )
        edges_result = await session.execute(edges_stmt)
        edges = edges_result.scalars().all()

        if not edges:
            return []

        # Resolve node → entity_id mapping
        node_ids = set()
        for e in edges:
            node_ids.add(e.from_node_id)
            node_ids.add(e.to_node_id)

        nodes_stmt = select(GraphNode).where(GraphNode.id.in_(list(node_ids)))
        nodes_result = await session.execute(nodes_stmt)
        nodes = nodes_result.scalars().all()

        node_to_entity: dict[str, str] = {str(n.id): str(n.entity_id) for n in nodes}
        entity_to_node: dict[str, str] = {str(n.entity_id): str(n.id) for n in nodes}

        # Build directed adjacency graph.  Keeping edges directed means A→B→A
        # only forms a cycle when there are explicit edges in both directions —
        # a genuine circular ownership loop.  A single undirected SAME_SOCIO
        # edge stored as A→B will not produce a false positive.
        entity_graph: dict[str, set[str]] = defaultdict(set)
        for edge in edges:
            from_entity = node_to_entity.get(str(edge.from_node_id))
            to_entity = node_to_entity.get(str(edge.to_node_id))
            if from_entity and to_entity:
                entity_graph[from_entity].add(to_entity)

        if not entity_graph:
            return []

        # Load recent contract events
        contracts_stmt = select(Event).where(
            Event.type == "contrato",
            Event.occurred_at >= window_start,
            Event.occurred_at <= window_end,
            Event.value_brl.isnot(None),
            Event.value_brl >= _MIN_INTRA_COMMUNITY_VALUE,
        )
        contracts_result = await session.execute(contracts_stmt)
        contracts = contracts_result.scalars().all()

        if not contracts:
            return []

        contract_ids = [c.id for c in contracts]
        parts_stmt = select(EventParticipant).where(
            EventParticipant.event_id.in_(contract_ids),
        )
        parts_result = await session.execute(parts_stmt)
        participants = parts_result.scalars().all()

        event_roles: dict[str, dict[str, set]] = defaultdict(lambda: defaultdict(set))
        for p in participants:
            event_roles[str(p.event_id)][p.role].add(str(p.entity_id))

        signals: list[RiskSignalOut] = []
        seen_cycles: set[str] = set()

        for contract in contracts:
            eid = str(contract.id)
            roles = event_roles.get(eid, {})
            winners = roles.get("winner", set()) | roles.get("supplier", set())
            subcontractors = roles.get("subcontractor", set()) | roles.get("subcontratado", set())
            buyers = roles.get("buyer", set()) | roles.get("procuring_entity", set())

            for winner_entity in winners:
                if winner_entity not in entity_graph:
                    continue

                # Find cycles from winner within max hops
                cycles = _find_cycles(entity_graph, winner_entity, _MAX_CYCLE_HOPS)
                if not cycles:
                    continue

                # Check for intra-community subcontractors
                community_entities = set(entity_graph.get(winner_entity, set()))
                for hop2 in list(community_entities):
                    community_entities.update(entity_graph.get(hop2, set()))

                intra_community_subcontractors = subcontractors & community_entities
                intra_value = contract.value_brl if intra_community_subcontractors else 0

                # Cycle key to dedup
                shortest_cycle = min(cycles, key=len)
                cycle_key = "->".join(sorted(shortest_cycle))
                if cycle_key in seen_cycles:
                    continue
                seen_cycles.add(cycle_key)

                if intra_value < _MIN_INTRA_COMMUNITY_VALUE and not intra_community_subcontractors:
                    # Still flag if cycle exists, but at lower severity
                    if contract.value_brl < _MIN_INTRA_COMMUNITY_VALUE * 2:
                        continue

                cycle_length = len(shortest_cycle) - 1
                community_size = len(community_entities) + 1
                ubo_convergence = cycle_length <= 2

                if ubo_convergence and intra_value > 0:
                    severity = SignalSeverity.CRITICAL
                    confidence = 0.75
                elif cycle_length <= 2 or intra_value > 0:
                    severity = SignalSeverity.HIGH
                    confidence = 0.65
                else:
                    severity = SignalSeverity.MEDIUM
                    confidence = 0.55

                entity_ids: list[uuid.UUID] = []
                for uid in list(winners | buyers)[:5]:
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
                        f"Lavagem via camadas societárias — ciclo de {cycle_length} salto(s) "
                        f"detectado (R$ {contract.value_brl:,.2f})"
                    ),
                    summary=(
                        f"Fornecedor vencedor forma ciclo societário de {cycle_length} salto(s) "
                        f"({' → '.join(shortest_cycle[:4])}...). "
                        f"Comunidade societária: {community_size} entidade(s). "
                        + (f"Subcontratados intra-comunidade: {len(intra_community_subcontractors)}. " if intra_community_subcontractors else "")
                        + f"Valor do contrato: R$ {contract.value_brl:,.2f}."
                    ),
                    factors={
                        "cycle_length": cycle_length,
                        "community_size": community_size,
                        "intra_community_value": round(intra_value, 2),
                        "ubo_convergence": ubo_convergence,
                        "n_intra_subcontractors": len(intra_community_subcontractors),
                    },
                    evidence_refs=[
                        EvidenceRef(
                            ref_type=RefType.EVENT,
                            ref_id=str(contract.id),
                            description=(
                                f"Contrato R$ {contract.value_brl:,.2f} com fornecedor "
                                f"em ciclo societário de {cycle_length} salto(s)"
                            ),
                        ),
                        EvidenceRef(
                            ref_type=RefType.ENTITY,
                            ref_id=winner_entity,
                            description=f"Fornecedor vencedor no ciclo: {' → '.join(shortest_cycle[:4])}",
                        ),
                    ],
                    entity_ids=entity_ids,
                    event_ids=[contract.id],
                    period_start=contract.occurred_at,
                    period_end=window_end,
                    created_at=datetime.now(timezone.utc),
                )
                signals.append(signal)

        return signals
