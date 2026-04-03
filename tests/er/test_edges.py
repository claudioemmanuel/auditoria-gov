import uuid

from shared.er.edges import build_structural_edges


def _participant(event_id, entity_id, role, value_brl=None):
    d = {"event_id": event_id, "entity_id": entity_id, "role": role}
    if value_brl is not None:
        d["value_brl"] = value_brl
    return d


class TestBuildStructuralEdges:
    def test_two_participants_one_edge(self):
        eid = uuid.uuid4()
        a, b = uuid.uuid4(), uuid.uuid4()
        participants = [
            _participant(eid, a, "buyer"),
            _participant(eid, b, "supplier"),
        ]
        edges = build_structural_edges(participants)
        assert len(edges) == 1
        assert edges[0].from_entity_id == a
        assert edges[0].to_entity_id == b
        assert edges[0].edge_type == "compra_fornecimento"
        assert edges[0].source_role == "buyer"
        assert edges[0].target_role == "supplier"
        assert edges[0].event_id == eid

    def test_three_participants_three_edges(self):
        eid = uuid.uuid4()
        a, b, c = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        participants = [
            _participant(eid, a, "buyer"),
            _participant(eid, b, "supplier"),
            _participant(eid, c, "guarantor"),
        ]
        edges = build_structural_edges(participants)
        assert len(edges) == 3

    def test_single_participant_no_edges(self):
        eid = uuid.uuid4()
        participants = [_participant(eid, uuid.uuid4(), "buyer")]
        edges = build_structural_edges(participants)
        assert len(edges) == 0

    def test_empty_participants(self):
        edges = build_structural_edges([])
        assert len(edges) == 0

    def test_multiple_events(self):
        e1, e2 = uuid.uuid4(), uuid.uuid4()
        a, b, c, d = uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        participants = [
            _participant(e1, a, "buyer"),
            _participant(e1, b, "supplier"),
            _participant(e2, c, "buyer"),
            _participant(e2, d, "supplier"),
        ]
        edges = build_structural_edges(participants)
        assert len(edges) == 2

    def test_weight_from_value(self):
        eid = uuid.uuid4()
        a, b = uuid.uuid4(), uuid.uuid4()
        participants = [
            _participant(eid, a, "buyer", value_brl=1_000_000),
            _participant(eid, b, "supplier"),
        ]
        edges = build_structural_edges(participants)
        assert edges[0].weight > 1.0  # log10(1_000_001)

    def test_default_weight_no_value(self):
        eid = uuid.uuid4()
        a, b = uuid.uuid4(), uuid.uuid4()
        participants = [
            _participant(eid, a, "buyer"),
            _participant(eid, b, "supplier"),
        ]
        edges = build_structural_edges(participants)
        assert edges[0].weight == 1.0

    def test_zero_value_default_weight(self):
        eid = uuid.uuid4()
        a, b = uuid.uuid4(), uuid.uuid4()
        participants = [
            _participant(eid, a, "buyer", value_brl=0),
            _participant(eid, b, "supplier"),
        ]
        edges = build_structural_edges(participants)
        assert edges[0].weight == 1.0
