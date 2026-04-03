import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from shared.models.canonical import (
    CanonicalEdge,
    CanonicalEntity,
    CanonicalEvent,
    CanonicalEventParticipant,
    NormalizeResult,
)
from shared.models.coverage import CoverageItem
from shared.models.graph import GraphEdgeOut, GraphNodeOut, NeighborhoodResponse
from shared.models.raw import RawItem, RawRunMeta
from shared.models.signals import (
    EvidenceRef,
    RefType,
    RiskSignalOut,
    SignalSeverity,
)


class TestCanonicalEntity:
    def test_create(self):
        e = CanonicalEntity(
            source_connector="pt",
            source_id="123",
            type="company",
            name="Test Corp",
        )
        assert e.name == "Test Corp"
        assert e.identifiers == {}
        assert e.attrs == {}

    def test_with_identifiers(self):
        e = CanonicalEntity(
            source_connector="pt",
            source_id="123",
            type="company",
            name="Test",
            identifiers={"cnpj": "11222333000181"},
        )
        assert e.identifiers["cnpj"] == "11222333000181"


class TestCanonicalEvent:
    def test_create_minimal(self):
        ev = CanonicalEvent(
            source_connector="pt",
            source_id="ev1",
            type="licitacao",
        )
        assert ev.participants == []
        assert ev.attrs == {}
        assert ev.value_brl is None

    def test_with_participants(self):
        entity = CanonicalEntity(
            source_connector="pt", source_id="e1", type="company", name="A"
        )
        p = CanonicalEventParticipant(entity_ref=entity, role="supplier")
        ev = CanonicalEvent(
            source_connector="pt",
            source_id="ev1",
            type="licitacao",
            participants=[p],
        )
        assert len(ev.participants) == 1
        assert ev.participants[0].role == "supplier"


class TestCanonicalEdge:
    def test_create(self):
        a = CanonicalEntity(source_connector="pt", source_id="1", type="company", name="A")
        b = CanonicalEntity(source_connector="pt", source_id="2", type="company", name="B")
        edge = CanonicalEdge(from_entity_ref=a, to_entity_ref=b, type="supplier")
        assert edge.weight == 1.0


class TestNormalizeResult:
    def test_empty(self):
        r = NormalizeResult()
        assert r.entities == []
        assert r.events == []
        assert r.edges == []

    def test_with_data(self):
        e = CanonicalEntity(source_connector="pt", source_id="1", type="company", name="A")
        r = NormalizeResult(entities=[e])
        assert len(r.entities) == 1


class TestRawItem:
    def test_create(self):
        item = RawItem(raw_id="123", data={"key": "value"})
        assert item.raw_id == "123"
        assert item.data == {"key": "value"}


class TestRawRunMeta:
    def test_defaults(self):
        meta = RawRunMeta(connector="pt", job="test")
        assert meta.items_fetched == 0
        assert meta.cursor_start is None


class TestGraphNodeOut:
    def test_create(self):
        node = GraphNodeOut(
            id=uuid.uuid4(),
            entity_id=uuid.uuid4(),
            label="Test",
            node_type="company",
        )
        assert node.attrs == {}


class TestGraphEdgeOut:
    def test_create(self):
        edge = GraphEdgeOut(
            id=uuid.uuid4(),
            from_node_id=uuid.uuid4(),
            to_node_id=uuid.uuid4(),
            type="supplier",
            weight=1.5,
        )
        assert edge.weight == 1.5


class TestNeighborhoodResponse:
    def test_empty(self):
        r = NeighborhoodResponse(center_node_id=uuid.uuid4())
        assert r.nodes == []
        assert r.edges == []
        assert r.depth == 1
        assert r.truncated is False


class TestSignalSeverity:
    def test_values(self):
        assert SignalSeverity.LOW == "low"
        assert SignalSeverity.MEDIUM == "medium"
        assert SignalSeverity.HIGH == "high"
        assert SignalSeverity.CRITICAL == "critical"


class TestRefType:
    def test_values(self):
        assert RefType.RAW_SOURCE == "raw_source"
        assert RefType.EVENT == "event"
        assert RefType.ENTITY == "entity"
        assert RefType.BASELINE == "baseline"
        assert RefType.EXTERNAL_URL == "external_url"


class TestEvidenceRef:
    def test_minimal(self):
        ref = EvidenceRef(ref_type=RefType.EVENT, description="Test")
        assert ref.ref_id is None
        assert ref.url is None

    def test_full(self):
        ref = EvidenceRef(
            ref_type=RefType.EXTERNAL_URL,
            ref_id="123",
            url="https://example.com",
            description="Test link",
        )
        assert ref.url == "https://example.com"


class TestRiskSignalOut:
    def test_create(self):
        signal = RiskSignalOut(
            id=uuid.uuid4(),
            typology_code="T01",
            typology_name="Test",
            severity=SignalSeverity.HIGH,
            confidence=0.85,
            title="Test signal",
            created_at=datetime.now(timezone.utc),
        )
        assert signal.confidence == 0.85
        assert signal.factors == {}
        assert signal.evidence_refs == []

    def test_confidence_bounds(self):
        with pytest.raises(ValidationError):
            RiskSignalOut(
                id=uuid.uuid4(),
                typology_code="T01",
                typology_name="Test",
                severity=SignalSeverity.LOW,
                confidence=1.5,  # > 1.0
                title="Test",
                created_at=datetime.now(timezone.utc),
            )


class TestCoverageItem:
    def test_create(self):
        item = CoverageItem(
            connector="pt",
            job="test",
            domain="licitacao",
            status="ok",
        )
        assert item.total_items == 0
        assert item.freshness_lag_hours is None

    def test_status_literal(self):
        for status in ("ok", "warning", "stale", "error", "pending"):
            item = CoverageItem(
                connector="pt", job="test", domain="d", status=status
            )
            assert item.status == status
