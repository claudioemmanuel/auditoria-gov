import math
import uuid
from dataclasses import dataclass


_INITIATOR_ROLES = {
    "buyer",
    "procuring_entity",
    "contracting_authority",
    "orgao",
    "senador",
    "deputado",
    "company",
}

_TARGET_ROLES = {
    "supplier",
    "winner",
    "fornecedor",
    "beneficiario",
    "payee",
    "partner",
}


@dataclass
class StructuralEdge:
    from_entity_id: uuid.UUID
    to_entity_id: uuid.UUID
    edge_type: str
    source_role: str
    target_role: str
    edge_label: str
    weight: float
    event_id: uuid.UUID
    occurred_at: object | None = None


def _edge_type_from_roles(source_role: str, target_role: str) -> str:
    source = source_role.lower()
    target = target_role.lower()
    if source in {"buyer", "procuring_entity"} and target in {"supplier", "winner", "fornecedor"}:
        return "compra_fornecimento"
    if source in {"senador", "deputado"} and target in {"supplier", "fornecedor", "beneficiario"}:
        return "agente_publico_favorecido"
    if source in {"buyer", "procuring_entity", "orgao"} and target in {"buyer", "procuring_entity", "orgao"}:
        return "coparticipacao_orgaos"
    if source in {"supplier", "winner", "fornecedor"} and target in {"supplier", "winner", "fornecedor"}:
        return "coparticipacao_fornecedores"
    if source == "company" and target == "partner":
        return "sociedade"
    return "coparticipacao_evento"


def _edge_label(source_role: str, target_role: str) -> str:
    if source_role.lower() in {"buyer", "procuring_entity"} and target_role.lower() in {"supplier", "winner", "fornecedor"}:
        return "Relacao de compra/fornecimento"
    if source_role.lower() == "company" and target_role.lower() == "partner":
        return "Relacao societaria (QSA)"
    return f"{source_role} -> {target_role}"


def _order_by_semantics(left: dict, right: dict) -> tuple[dict, dict]:
    left_role = str(left.get("role") or "").lower()
    right_role = str(right.get("role") or "").lower()

    if left_role in _INITIATOR_ROLES and right_role in _TARGET_ROLES:
        return left, right
    if right_role in _INITIATOR_ROLES and left_role in _TARGET_ROLES:
        return right, left
    if left_role in _INITIATOR_ROLES and right_role not in _INITIATOR_ROLES:
        return left, right
    if right_role in _INITIATOR_ROLES and left_role not in _INITIATOR_ROLES:
        return right, left

    left_id = str(left.get("entity_id"))
    right_id = str(right.get("entity_id"))
    if left_id <= right_id:
        return left, right
    return right, left


def build_structural_edges(
    participants: list[dict],
) -> list[StructuralEdge]:
    """Build graph edges from event-participant relationships.

    For each event with multiple participants, create directional edges
    with a stable semantic order and user-facing edge categories.
    """
    events: dict[uuid.UUID, list[dict]] = {}
    for participant in participants:
        events.setdefault(participant["event_id"], []).append(participant)

    edges: list[StructuralEdge] = []
    for event_id, parts in events.items():
        if len(parts) < 2:
            continue

        for i in range(len(parts)):
            for j in range(i + 1, len(parts)):
                left, right = _order_by_semantics(parts[i], parts[j])
                source_role = str(left.get("role") or "unknown")
                target_role = str(right.get("role") or "unknown")
                edge_type = _edge_type_from_roles(source_role, target_role)

                weight = 1.0
                value = parts[i].get("value_brl") or parts[j].get("value_brl")
                if value and value > 0:
                    weight = math.log10(value + 1)

                edges.append(
                    StructuralEdge(
                        from_entity_id=left["entity_id"],
                        to_entity_id=right["entity_id"],
                        edge_type=edge_type,
                        source_role=source_role,
                        target_role=target_role,
                        edge_label=_edge_label(source_role, target_role),
                        weight=weight,
                        event_id=event_id,
                        occurred_at=left.get("occurred_at") or right.get("occurred_at"),
                    )
                )

    return edges
