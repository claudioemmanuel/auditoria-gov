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

# Graph edge types indicating relational conflict of interest.
# Only includes types actively produced by shared/er/corporate_edges.py.
_CONFLICT_EDGE_TYPES = {
    "SAME_ADDRESS",
    "SHARES_PHONE",
    "SAME_SOCIO",
    "SAME_ACCOUNTANT",
}

# Minimum number of shared indicators to flag
_MIN_SHARED_INDICATORS = 2

# Minimum score to generate a signal
_MIN_RELATIONSHIP_SCORE = 0.6


def _edge_weight(edge_type: str) -> float:
    """Weight for each relationship indicator in the composite score."""
    weights = {
        "SAME_SOCIO": 0.4,
        "SAME_ACCOUNTANT": 0.35,
        "SAME_ADDRESS": 0.30,
        "SHARES_PHONE": 0.25,
    }
    return weights.get(edge_type, 0.15)


class T13ConflictOfInterestTypology(BaseTypology):
    """T13 — Conflito de Interesses / Nepotismo Relacional.

    Algorithm:
    1. Load graph edges of types indicating relational conflicts
       (SAME_ADDRESS, KINSHIP, SAME_SOCIO, SAME_ACCOUNTANT, etc.).
    2. Resolve from/to entity_ids via GraphNode.
    3. Build a conflict graph: set of connected entity pairs.
    4. Query EventParticipants for recent licitacoes/contratos:
       - winner/supplier on one side
       - buyer/procuring_entity on the other
    5. Flag (buyer, winner) pairs where the entities are connected
       in the conflict graph.
    6. Compute relationship_score as weighted sum of shared indicators.

    Legal basis:
    - Lei 12.813/2013, Arts. 5°-6° (conflict of interest for public agents)
    - Lei 14.133/2021, Art. 9° (prohibition on kinship conflicts up to 3rd degree)
    - Decreto 7.203/2010 (anti-nepotism regulation in public administration)
    - TCU Acórdão 1798/2024 (shared kinship + IP address = procurement fraud)
    """

    @property
    def id(self) -> str:
        return "T13"

    @property
    def name(self) -> str:
        return "Conflito de Interesses"

    @property
    def required_domains(self) -> list[str]:
        return ["licitacao", "empresa"]

    @property
    def required_fields(self) -> list[str]:
        return ["graph_edges"]

    @property
    def corruption_types(self) -> list[str]:
        return ["nepotismo_clientelismo", "corrupcao_ativa_passiva"]

    @property
    def spheres(self) -> list[str]:
        return ["administrativa", "politica"]

    @property
    def evidence_level(self) -> str:
        return "indirect"

    async def run(self, session) -> list[RiskSignalOut]:
        window_end = datetime.now(timezone.utc)
        window_start = window_end - timedelta(days=365 * 5)  # 5-year window to cover historical ingest

        # Query graph edges indicating relational conflicts
        edges_stmt = select(GraphEdge).where(
            GraphEdge.type.in_(_CONFLICT_EDGE_TYPES),
        )
        edges_result = await session.execute(edges_stmt)
        edges = edges_result.scalars().all()

        if not edges:
            return []

        # Resolve graph node entity_ids
        node_ids = set()
        for e in edges:
            node_ids.add(e.from_node_id)
            node_ids.add(e.to_node_id)

        nodes_stmt = select(GraphNode).where(GraphNode.id.in_(list(node_ids)))
        nodes_result = await session.execute(nodes_stmt)
        nodes = nodes_result.scalars().all()

        node_entity: dict[str, uuid.UUID] = {str(n.id): n.entity_id for n in nodes}

        # Build conflict graph: entity_id → {connected_entity_id → [(edge_type, weight)]}
        conflict_links: dict[str, dict[str, list[tuple[str, float]]]] = defaultdict(lambda: defaultdict(list))
        for edge in edges:
            from_entity = node_entity.get(str(edge.from_node_id))
            to_entity = node_entity.get(str(edge.to_node_id))
            if not from_entity or not to_entity:
                continue
            w = _edge_weight(edge.type)
            conflict_links[str(from_entity)][str(to_entity)].append((edge.type, w))
            conflict_links[str(to_entity)][str(from_entity)].append((edge.type, w))

        if not conflict_links:
            return []

        # Query recent procurement event participants
        events_stmt = select(Event).where(
            Event.type.in_(["licitacao", "contrato"]),
            Event.occurred_at >= window_start,
            Event.occurred_at <= window_end,
        )
        events_result = await session.execute(events_stmt)
        events = events_result.scalars().all()

        if not events:
            return []

        event_map = {str(e.id): e for e in events}
        event_ids = [e.id for e in events]

        parts_stmt = select(EventParticipant).where(
            EventParticipant.event_id.in_(event_ids),
        )
        parts_result = await session.execute(parts_stmt)
        participants = parts_result.scalars().all()

        # Build event → {role → [entity_ids]}
        event_roles: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
        for p in participants:
            event_roles[str(p.event_id)][p.role].append(str(p.entity_id))

        signals: list[RiskSignalOut] = []
        seen_pairs: set[tuple[str, str]] = set()

        for eid, roles in event_roles.items():
            buyers = set(roles.get("buyer", []) + roles.get("procuring_entity", []))
            suppliers = set(roles.get("winner", []) + roles.get("supplier", []))

            for buyer_id in buyers:
                buyer_links = conflict_links.get(buyer_id, {})
                for supplier_id in suppliers:
                    if supplier_id not in buyer_links:
                        continue

                    pair_key = (min(buyer_id, supplier_id), max(buyer_id, supplier_id))
                    if pair_key in seen_pairs:
                        continue
                    seen_pairs.add(pair_key)

                    indicators = buyer_links[supplier_id]
                    n_shared = len(indicators)
                    if n_shared < _MIN_SHARED_INDICATORS:
                        continue

                    # Compute relationship score (cap at 1.0)
                    relationship_score = min(1.0, sum(w for _, w in indicators))
                    if relationship_score < _MIN_RELATIONSHIP_SCORE:
                        continue

                    indicator_types = [t for t, _ in indicators]

                    if relationship_score >= 0.85:
                        severity = SignalSeverity.CRITICAL
                        confidence = min(0.90, 0.75 + relationship_score * 0.15)
                    elif relationship_score >= 0.70:
                        severity = SignalSeverity.HIGH
                        confidence = 0.70
                    else:
                        severity = SignalSeverity.MEDIUM
                        confidence = 0.55

                    event_obj = event_map.get(eid)
                    entity_ids: list[uuid.UUID] = []
                    for uid in [buyer_id, supplier_id]:
                        try:
                            entity_ids.append(uuid.UUID(uid))
                        except ValueError:
                            pass

                    # Find all affected events for this pair
                    affected_events = [
                        e for e in events
                        if buyer_id in event_roles.get(str(e.id), {}).get("buyer", [])
                        + event_roles.get(str(e.id), {}).get("procuring_entity", [])
                        and supplier_id in event_roles.get(str(e.id), {}).get("winner", [])
                        + event_roles.get(str(e.id), {}).get("supplier", [])
                    ]

                    n_contracts = len(affected_events)

                    signal = RiskSignalOut(
                        id=uuid.uuid4(),
                        typology_code=self.id,
                        typology_name=self.name,
                        severity=severity,
                        confidence=confidence,
                        title=(
                            f"Conflito de interesses — {n_shared} indicador(es) "
                            f"de vínculo entre contratante e fornecedor"
                        ),
                        summary=(
                            f"Entidades vinculadas por: {', '.join(indicator_types)}. "
                            f"Score de relacionamento: {relationship_score:.2f}. "
                            f"{n_contracts} contrato(s)/licitação(ões) afetado(s)."
                        ),
                        factors={
                            "relationship_score": round(relationship_score, 3),
                            "n_shared_indicators": n_shared,
                            "n_contracts_affected": n_contracts,
                            "indicator_types": indicator_types,
                        },
                        evidence_refs=[
                            EvidenceRef(
                                ref_type=RefType.ENTITY,
                                ref_id=buyer_id,
                                description=f"Entidade contratante com {n_shared} vínculo(s) com fornecedor",
                            ),
                            EvidenceRef(
                                ref_type=RefType.ENTITY,
                                ref_id=supplier_id,
                                description=f"Fornecedor vinculado ao contratante via: {', '.join(indicator_types)}",
                            ),
                        ] + [
                            EvidenceRef(
                                ref_type=RefType.EVENT,
                                ref_id=str(e.id),
                                description=(
                                    f"Contrato/licitação R$ {e.value_brl:,.2f} "
                                    f"em {e.occurred_at.strftime('%d/%m/%Y') if e.occurred_at else 'N/A'}"
                                    if e.value_brl else
                                    f"Evento em {e.occurred_at.strftime('%d/%m/%Y') if e.occurred_at else 'N/A'}"
                                ),
                            )
                            for e in affected_events[:3]
                        ],
                        entity_ids=entity_ids,
                        event_ids=[e.id for e in affected_events[:10]],
                        period_start=window_start,
                        period_end=window_end,
                        created_at=datetime.now(timezone.utc),
                    )
                    signals.append(signal)

        return signals
