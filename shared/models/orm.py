import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.models.base import Base


class RawRun(Base):
    __tablename__ = "raw_run"

    connector: Mapped[str] = mapped_column(String(100))
    job: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20), default="running")
    cursor_start: Mapped[Optional[str]] = mapped_column(String(255))
    cursor_end: Mapped[Optional[str]] = mapped_column(String(255))
    items_fetched: Mapped[int] = mapped_column(Integer, default=0)
    items_normalized: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[Optional[dict]] = mapped_column(JSONB)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    sources: Mapped[list["RawSource"]] = relationship(back_populates="run")


class RawSource(Base):
    __tablename__ = "raw_source"

    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("raw_run.id")
    )
    connector: Mapped[str] = mapped_column(String(100))
    job: Mapped[str] = mapped_column(String(100))
    raw_id: Mapped[str] = mapped_column(String(255))
    raw_data: Mapped[dict] = mapped_column(JSONB)
    normalized: Mapped[bool] = mapped_column(default=False)

    run: Mapped["RawRun"] = relationship(back_populates="sources")


class Entity(Base):
    __tablename__ = "entity"

    type: Mapped[str] = mapped_column(String(50))  # person, company, org
    name: Mapped[str] = mapped_column(String(500))
    name_normalized: Mapped[str] = mapped_column(String(500))
    identifiers: Mapped[dict] = mapped_column(JSONB, default=dict)
    attrs: Mapped[dict] = mapped_column(JSONB, default=dict)
    cluster_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    er_processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    cluster_confidence: Mapped[Optional[int]] = mapped_column(
        Integer, CheckConstraint("cluster_confidence BETWEEN 0 AND 100"), nullable=True
    )

    aliases: Mapped[list["EntityAlias"]] = relationship(back_populates="entity")

    __table_args__ = (
        Index("ix_entity_identifiers_cnpj", identifiers["cnpj"].as_string()),
        Index("ix_entity_type_name_norm", "type", "name_normalized"),
        Index("ix_entity_cluster_id", "cluster_id", postgresql_where="cluster_id IS NOT NULL"),
    )


class EntityAlias(Base):
    __tablename__ = "entity_alias"

    entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("entity.id")
    )
    alias_type: Mapped[str] = mapped_column(String(50))
    value: Mapped[str] = mapped_column(String(500))
    source: Mapped[str] = mapped_column(String(100))

    entity: Mapped["Entity"] = relationship(back_populates="aliases")


class ERMergeEvidence(Base):
    __tablename__ = "er_merge_evidence"

    # id and created_at are inherited from Base — do not redefine
    entity_a_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("entity.id"), nullable=False)
    entity_b_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("entity.id"), nullable=False)
    confidence_score: Mapped[int] = mapped_column(
        Integer, CheckConstraint("confidence_score BETWEEN 0 AND 100"), nullable=False
    )
    evidence_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # cnpj_exact | cpf_exact | name_fuzzy | co_participation
    evidence_detail: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        Index("ix_er_merge_evidence_entity_a", "entity_a_id"),
        Index("ix_er_merge_evidence_entity_b", "entity_b_id"),
    )


class Event(Base):
    __tablename__ = "event"

    type: Mapped[str] = mapped_column(String(100))
    subtype: Mapped[Optional[str]] = mapped_column(String(100))
    description: Mapped[Optional[str]] = mapped_column(Text)
    occurred_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    source_connector: Mapped[str] = mapped_column(String(100))
    source_id: Mapped[str] = mapped_column(String(255))
    value_brl: Mapped[Optional[float]] = mapped_column(Float)
    attrs: Mapped[dict] = mapped_column(JSONB, default=dict)

    participants: Mapped[list["EventParticipant"]] = relationship(
        back_populates="event"
    )

    __table_args__ = (
        Index("ix_event_type_occurred_at", "type", "occurred_at"),
        UniqueConstraint("source_connector", "source_id", name="uq_event_source"),
    )


class EventParticipant(Base):
    __tablename__ = "event_participant"

    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("event.id")
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("entity.id")
    )
    role: Mapped[str] = mapped_column(String(50))
    attrs: Mapped[dict] = mapped_column(JSONB, default=dict)

    event: Mapped["Event"] = relationship(back_populates="participants")
    entity: Mapped["Entity"] = relationship()

    __table_args__ = (
        Index("ix_event_participant_entity_role", "entity_id", "role"),
        Index("ix_event_participant_event_role", "event_id", "role"),
        UniqueConstraint("event_id", "entity_id", "role", name="uq_event_participant_triplet"),
    )


class GraphNode(Base):
    __tablename__ = "graph_node"

    entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("entity.id"), unique=True
    )
    label: Mapped[str] = mapped_column(String(500))
    node_type: Mapped[str] = mapped_column(String(50))
    attrs: Mapped[dict] = mapped_column(JSONB, default=dict)

    entity: Mapped["Entity"] = relationship()


class GraphEdge(Base):
    __tablename__ = "graph_edge"

    from_node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("graph_node.id")
    )
    to_node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("graph_node.id")
    )
    type: Mapped[str] = mapped_column(String(100))
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    edge_strength: Mapped[str] = mapped_column(String(20), default="weak")
    verification_method: Mapped[Optional[str]] = mapped_column(String(100))
    verification_confidence: Mapped[Optional[float]] = mapped_column(Float)
    attrs: Mapped[dict] = mapped_column(JSONB, default=dict)

    from_node: Mapped["GraphNode"] = relationship(foreign_keys=[from_node_id])
    to_node: Mapped["GraphNode"] = relationship(foreign_keys=[to_node_id])

    __table_args__ = (
        Index("ix_graph_edge_from", "from_node_id"),
        Index("ix_graph_edge_to", "to_node_id"),
        Index("ix_graph_edge_type", "type"),
        Index("ix_graph_edge_strength", "edge_strength"),
        UniqueConstraint("from_node_id", "to_node_id", "type", name="uq_graph_edge_triplet"),
    )


class TextCorpus(Base):
    __tablename__ = "text_corpus"

    source_type: Mapped[str] = mapped_column(String(100))
    source_id: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)
    attrs: Mapped[dict] = mapped_column(JSONB, default=dict)


class TextEmbedding(Base):
    __tablename__ = "text_embedding"

    corpus_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("text_corpus.id")
    )
    model: Mapped[str] = mapped_column(String(100))
    embedding: Mapped[list] = mapped_column(Vector(1536))

    corpus: Mapped["TextCorpus"] = relationship()

    __table_args__ = (
        Index(
            "ix_text_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )


class Typology(Base):
    __tablename__ = "typology"

    code: Mapped[str] = mapped_column(String(10), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[Optional[str]] = mapped_column(Text)
    required_domains: Mapped[list] = mapped_column(JSONB, default=list)
    active: Mapped[bool] = mapped_column(default=True)


class EvidencePackage(Base):
    __tablename__ = "evidence_package"

    source_url: Mapped[Optional[str]] = mapped_column(Text)
    source_hash: Mapped[Optional[str]] = mapped_column(String(128))
    captured_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    parser_version: Mapped[Optional[str]] = mapped_column(String(100))
    model_version: Mapped[Optional[str]] = mapped_column(String(100))
    raw_snapshot_uri: Mapped[Optional[str]] = mapped_column(Text)
    normalized_snapshot_uri: Mapped[Optional[str]] = mapped_column(Text)
    signature: Mapped[Optional[str]] = mapped_column(String(128))

    __table_args__ = (
        Index("ix_evidence_package_captured_at", "captured_at"),
        Index("ix_evidence_package_signature", "signature"),
    )


class RiskSignal(Base):
    __tablename__ = "risk_signal"

    typology_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("typology.id")
    )
    severity: Mapped[str] = mapped_column(String(20))
    confidence: Mapped[float] = mapped_column(Float)
    title: Mapped[str] = mapped_column(String(500))
    summary: Mapped[Optional[str]] = mapped_column(Text)
    explanation_md: Mapped[Optional[str]] = mapped_column(Text)
    completeness_score: Mapped[float] = mapped_column(Float, default=0.0)
    completeness_status: Mapped[str] = mapped_column(String(20), default="insufficient")
    evidence_package_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("evidence_package.id")
    )
    factors: Mapped[dict] = mapped_column(JSONB, default=dict)
    evidence_refs: Mapped[list] = mapped_column(JSONB, default=list)
    entity_ids: Mapped[list] = mapped_column(JSONB, default=list)
    event_ids: Mapped[list] = mapped_column(JSONB, default=list)
    period_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    period_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    # Dedup key: hash(typology_code, sorted(entity_ids), period_start, period_end).
    # Prevents duplicate signals for the same scope+window across runs.
    dedup_key: Mapped[Optional[str]] = mapped_column(String(64), unique=True)
    signal_confidence_score: Mapped[Optional[int]] = mapped_column(
        Integer, CheckConstraint("signal_confidence_score BETWEEN 0 AND 100"), nullable=True
    )
    confidence_factors: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    typology: Mapped["Typology"] = relationship()
    evidence_package: Mapped[Optional["EvidencePackage"]] = relationship()

    __table_args__ = (
        Index("ix_risk_signal_typology_severity", "typology_id", "severity", "created_at"),
        Index("ix_risk_signal_completeness", "completeness_status", "completeness_score"),
    )


class Case(Base):
    __tablename__ = "case"

    title: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), default="open")
    severity: Mapped[str] = mapped_column(String(20))
    summary: Mapped[Optional[str]] = mapped_column(Text)
    case_type: Mapped[Optional[str]] = mapped_column(String(50))
    case_category: Mapped[Optional[str]] = mapped_column(String(50))
    attrs: Mapped[dict] = mapped_column(JSONB, default=dict)

    items: Mapped[list["CaseItem"]] = relationship(back_populates="case")


class CaseItem(Base):
    __tablename__ = "case_item"

    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("case.id")
    )
    signal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("risk_signal.id")
    )

    case: Mapped["Case"] = relationship(back_populates="items")
    signal: Mapped["RiskSignal"] = relationship()


class Contestation(Base):
    __tablename__ = "contestation"

    signal_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("risk_signal.id")
    )
    status: Mapped[str] = mapped_column(String(20), default="open")
    requester_name: Mapped[str] = mapped_column(String(255))
    requester_email: Mapped[Optional[str]] = mapped_column(String(255))
    reason: Mapped[str] = mapped_column(Text)
    details: Mapped[dict] = mapped_column(JSONB, default=dict)
    resolution: Mapped[Optional[str]] = mapped_column(Text)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    signal: Mapped[Optional["RiskSignal"]] = relationship()

    __table_args__ = (
        Index("ix_contestation_signal_status", "signal_id", "status"),
        Index("ix_contestation_created_at", "created_at"),
    )


class IngestState(Base):
    __tablename__ = "ingest_state"

    connector: Mapped[str] = mapped_column(String(100))
    job: Mapped[str] = mapped_column(String(100))
    last_cursor: Mapped[Optional[str]] = mapped_column(String(255))
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    yield_requested: Mapped[bool] = mapped_column(default=False, server_default="false")

    __table_args__ = (
        UniqueConstraint("connector", "job", name="uq_ingest_state_connector_job"),
    )


class DispensaThreshold(Base):
    """Legal thresholds for dispensa de licitação, versioned by decree.

    Allows updating limits when government decrees change (e.g. Decreto 12.807/2025)
    without code deployments.
    """

    __tablename__ = "dispensa_threshold"
    __table_args__ = (
        UniqueConstraint("categoria", "valid_from", name="uq_dispensa_threshold_cat_from"),
    )

    # Override Base id: use integer autoincrement PK for simplicity
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    categoria: Mapped[str] = mapped_column(String(50))   # goods | works | rd | vehicle
    valor_brl: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    valid_from: Mapped[date] = mapped_column(Date)
    valid_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    decreto_ref: Mapped[str] = mapped_column(String(100))


class CoverageRegistry(Base):
    __tablename__ = "coverage_registry"

    connector: Mapped[str] = mapped_column(String(100))
    job: Mapped[str] = mapped_column(String(100))
    domain: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    last_success_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True)
    )
    freshness_lag_hours: Mapped[Optional[float]] = mapped_column(Float)
    total_items: Mapped[int] = mapped_column(BigInteger, default=0)
    period_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    period_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    veracity_score: Mapped[Optional[float]] = mapped_column(Float)
    veracity_label: Mapped[Optional[str]] = mapped_column(String(20))
    domain_tier: Mapped[Optional[str]] = mapped_column(String(50))
    last_compliance_check_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True)
    )
    compliance_status: Mapped[Optional[str]] = mapped_column(String(20))

    __table_args__ = (
        UniqueConstraint(
            "connector", "job", name="uq_coverage_registry_connector_job"
        ),
    )


class BaselineSnapshot(Base):
    __tablename__ = "baseline_snapshot"

    baseline_type: Mapped[str] = mapped_column(String(50))
    scope_key: Mapped[str] = mapped_column(String(255))
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    sample_size: Mapped[int] = mapped_column(Integer)
    metrics: Mapped[dict] = mapped_column(JSONB)

    __table_args__ = (
        UniqueConstraint(
            "baseline_type",
            "scope_key",
            "window_start",
            "window_end",
            name="uq_baseline_snapshot",
        ),
    )


class ERRunState(Base):
    __tablename__ = "er_run_state"

    status: Mapped[str] = mapped_column(String(20))
    entities_processed: Mapped[int] = mapped_column(Integer, default=0)
    deterministic_matches: Mapped[int] = mapped_column(Integer, default=0)
    probabilistic_matches: Mapped[int] = mapped_column(Integer, default=0)
    clusters_formed: Mapped[int] = mapped_column(Integer, default=0)
    edges_created: Mapped[int] = mapped_column(Integer, default=0)
    watermark_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class TypologyRunLog(Base):
    __tablename__ = "typology_run_log"

    typology_code: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(20))  # running, success, error
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer)
    candidates: Mapped[int] = mapped_column(Integer, default=0)
    signals_created: Mapped[int] = mapped_column(Integer, default=0)
    signals_deduped: Mapped[int] = mapped_column(Integer, default=0)
    signals_blocked: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    dry_run: Mapped[bool] = mapped_column(Boolean, default=False)

    __table_args__ = (
        Index("ix_typology_run_log_code_started", "typology_code", "started_at"),
    )


class EventRawSource(Base):
    """M2M link: Event ↔ RawSource — traces an event back to its raw API JSON."""

    __tablename__ = "event_raw_source"

    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("event.id", ondelete="CASCADE")
    )
    raw_source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("raw_source.id", ondelete="CASCADE")
    )

    event: Mapped["Event"] = relationship()
    raw_source: Mapped["RawSource"] = relationship()

    __table_args__ = (
        UniqueConstraint("event_id", "raw_source_id", name="uq_event_raw_source"),
        Index("ix_event_raw_source_event", "event_id"),
        Index("ix_event_raw_source_raw_source", "raw_source_id"),
    )


class EntityRawSource(Base):
    """M2M link: Entity ↔ RawSource — traces an entity back to its raw API JSON."""

    __tablename__ = "entity_raw_source"

    entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("entity.id", ondelete="CASCADE")
    )
    raw_source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("raw_source.id", ondelete="CASCADE")
    )

    entity: Mapped["Entity"] = relationship()
    raw_source: Mapped["RawSource"] = relationship()

    __table_args__ = (
        UniqueConstraint("entity_id", "raw_source_id", name="uq_entity_raw_source"),
        Index("ix_entity_raw_source_entity", "entity_id"),
        Index("ix_entity_raw_source_raw_source", "raw_source_id"),
    )


class SignalEvent(Base):
    """M2M link: RiskSignal ↔ Event — proper FK replacing JSONB event_ids."""

    __tablename__ = "signal_event"

    signal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("risk_signal.id", ondelete="CASCADE")
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("event.id", ondelete="CASCADE")
    )

    signal: Mapped["RiskSignal"] = relationship()
    event: Mapped["Event"] = relationship()

    __table_args__ = (
        UniqueConstraint("signal_id", "event_id", name="uq_signal_event"),
        Index("ix_signal_event_signal", "signal_id"),
        Index("ix_signal_event_event", "event_id"),
    )


class SignalEntity(Base):
    """M2M link: RiskSignal ↔ Entity — proper FK replacing JSONB entity_ids."""

    __tablename__ = "signal_entity"

    signal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("risk_signal.id", ondelete="CASCADE")
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("entity.id", ondelete="CASCADE")
    )

    signal: Mapped["RiskSignal"] = relationship()
    entity: Mapped["Entity"] = relationship()

    __table_args__ = (
        UniqueConstraint("signal_id", "entity_id", name="uq_signal_entity"),
        Index("ix_signal_entity_signal", "signal_id"),
        Index("ix_signal_entity_entity", "entity_id"),
    )


class ReferenceData(Base):
    __tablename__ = "reference_data"

    category: Mapped[str] = mapped_column(String(50))
    code: Mapped[str] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(500))
    parent_code: Mapped[Optional[str]] = mapped_column(String(50))
    attrs: Mapped[dict] = mapped_column(JSONB, default=dict)

    __table_args__ = (
        UniqueConstraint("category", "code", name="uq_reference_data_category_code"),
        Index("ix_reference_data_category", "category"),
    )


class SignalEvidence(Base):
    __tablename__ = "signal_evidence"

    signal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("risk_signal.id", ondelete="CASCADE")
    )
    dataset: Mapped[str] = mapped_column(Text)
    record_id: Mapped[str] = mapped_column(Text)
    field_name: Mapped[Optional[str]] = mapped_column(Text)
    field_value: Mapped[Optional[str]] = mapped_column(Text)
    reference_url: Mapped[Optional[str]] = mapped_column(Text)

    signal: Mapped["RiskSignal"] = relationship()

    __table_args__ = (
        Index("ix_signal_evidence_signal", "signal_id"),
    )


class LegalViolationHypothesis(Base):
    __tablename__ = "legal_violation_hypothesis"

    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("case.id", ondelete="CASCADE")
    )
    signal_cluster: Mapped[list] = mapped_column(ARRAY(Text), default=list)
    law_name: Mapped[str] = mapped_column(Text)
    article: Mapped[Optional[str]] = mapped_column(Text)
    violation_type: Mapped[Optional[str]] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)

    case: Mapped["Case"] = relationship()

    __table_args__ = (
        Index("ix_legal_hypothesis_case", "case_id"),
        UniqueConstraint("case_id", "law_name", "article", name="uq_legal_hypothesis_case_law"),
    )
