import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class GraphNodeOut(BaseModel):
    id: uuid.UUID
    entity_id: uuid.UUID
    label: str
    node_type: str
    attrs: dict = Field(default_factory=dict)


class GraphEdgeOut(BaseModel):
    id: uuid.UUID
    from_node_id: uuid.UUID
    to_node_id: uuid.UUID
    type: str
    weight: float
    edge_strength: str = "weak"
    verification_method: str | None = None
    verification_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    attrs: dict = Field(default_factory=dict)


class GraphDiagnosticsOut(BaseModel):
    graph_materialized: bool = False
    entity_event_count: int = 0
    co_participant_count: int = 0
    reason: str = "no_coparticipants_or_er_not_run"


class VirtualCenterNodeOut(BaseModel):
    entity_id: uuid.UUID
    label: str
    node_type: str


class CoParticipantOut(BaseModel):
    entity_id: uuid.UUID
    label: str
    node_type: str
    shared_events: int = 0


class NeighborhoodResponse(BaseModel):
    center_node_id: uuid.UUID
    nodes: list[GraphNodeOut] = Field(default_factory=list)
    edges: list[GraphEdgeOut] = Field(default_factory=list)
    depth: int = 1
    truncated: bool = False
    diagnostics: GraphDiagnosticsOut | None = None
    virtual_center_node: VirtualCenterNodeOut | None = None
    co_participants: list[CoParticipantOut] = Field(default_factory=list)


class CaseSignalBrief(BaseModel):
    id: uuid.UUID
    typology_code: str
    typology_name: str
    severity: str
    confidence: float
    title: str
    summary: str | None = None
    entity_ids: list[uuid.UUID] = Field(default_factory=list)


class CaseFocusSignalSummary(BaseModel):
    id: uuid.UUID
    typology_code: str
    typology_name: str
    severity: str
    confidence: float
    title: str
    summary: str | None = None
    period_start: datetime | None = None
    period_end: datetime | None = None
    pattern_label: str | None = None


class CaseGraphResponse(BaseModel):
    case_id: uuid.UUID
    case_title: str
    case_severity: str
    case_status: str
    seed_entity_ids: list[uuid.UUID] = Field(default_factory=list)
    nodes: list[GraphNodeOut] = Field(default_factory=list)
    edges: list[GraphEdgeOut] = Field(default_factory=list)
    signals: list[CaseSignalBrief] = Field(default_factory=list)
    truncated: bool = False
    er_pending: bool = False
    focus_signal_summary: CaseFocusSignalSummary | None = None
    focus_entity_ids: list[uuid.UUID] = Field(default_factory=list)
    focus_edge_ids: list[uuid.UUID] = Field(default_factory=list)


class SignalGraphSignalOut(BaseModel):
    id: uuid.UUID
    typology_code: str
    typology_name: str
    severity: str
    confidence: float
    title: str
    period_start: datetime | None = None
    period_end: datetime | None = None


class SignalStoryActorOut(BaseModel):
    entity_id: uuid.UUID
    name: str
    node_type: str
    roles: list[str] = Field(default_factory=list)
    event_count: int = 0


class SignalPatternStoryOut(BaseModel):
    pattern_label: str
    started_at: datetime | None = None
    ended_at: datetime | None = None
    started_from_entities: list[SignalStoryActorOut] = Field(default_factory=list)
    flow_targets: list[SignalStoryActorOut] = Field(default_factory=list)
    why_flagged: str


class SignalGraphNodeOut(BaseModel):
    id: uuid.UUID
    entity_id: uuid.UUID
    label: str
    node_type: str
    attrs: dict = Field(default_factory=dict)


class SignalGraphEdgeOut(BaseModel):
    id: str
    from_node_id: uuid.UUID
    to_node_id: uuid.UUID
    type: str
    label: str
    weight: float
    evidence_event_ids: list[uuid.UUID] = Field(default_factory=list)
    first_seen_at: datetime | None = None
    last_seen_at: datetime | None = None
    attrs: dict = Field(default_factory=dict)


class ExpandedNodeOut(BaseModel):
    id: uuid.UUID
    entity_id: uuid.UUID
    label: str
    node_type: str
    source_connector: str | None = None
    attrs: dict = Field(default_factory=dict)
    is_direct_participant: bool = False


class ExpansionEdgeOut(BaseModel):
    id: uuid.UUID
    from_entity_id: uuid.UUID
    to_entity_id: uuid.UUID
    edge_type: str
    weight: float = 1.0
    attrs: dict = Field(default_factory=dict)


class ClusterEntityOut(BaseModel):
    entity_id: uuid.UUID
    name: str
    node_type: str
    source_connector: str | None = None


class SignalGraphOverviewOut(BaseModel):
    nodes: list[SignalGraphNodeOut] = Field(default_factory=list)
    edges: list[SignalGraphEdgeOut] = Field(default_factory=list)
    expanded_nodes: list[ExpandedNodeOut] = Field(default_factory=list)
    expansion_edges: list[ExpansionEdgeOut] = Field(default_factory=list)


class SignalTimelineParticipantOut(BaseModel):
    entity_id: uuid.UUID
    name: str
    node_type: str
    role: str
    role_label: str


class SignalTimelineEventOut(BaseModel):
    event_id: uuid.UUID
    occurred_at: datetime | None = None
    value_brl: float | None = None
    description: str
    source_connector: str
    source_id: str
    participants: list[SignalTimelineParticipantOut] = Field(default_factory=list)
    evidence_reason: str
    attrs: dict = Field(default_factory=dict)


class SignalInvolvedEntityRoleOut(BaseModel):
    code: str
    label: str
    count_in_signal: int


class SignalInvolvedEntityProfileOut(BaseModel):
    entity_id: uuid.UUID
    name: str
    node_type: str
    identifiers: dict = Field(default_factory=dict)
    attrs: dict = Field(default_factory=dict)
    photo_url: str | None = None
    roles_in_signal: list[SignalInvolvedEntityRoleOut] = Field(default_factory=list)
    event_count: int = 0
    is_direct_participant: bool = True
    cluster_entities: list[ClusterEntityOut] = Field(default_factory=list)


class PathHopOut(BaseModel):
    from_entity_id: uuid.UUID
    to_entity_id: uuid.UUID
    from_label: str
    to_label: str
    edge_type: str
    first_seen_at: datetime | None = None
    last_seen_at: datetime | None = None


class EntityPathResponse(BaseModel):
    found: bool
    hops: int | None = None
    path: list[PathHopOut] = Field(default_factory=list)


class SignalGraphDiagnosticsOut(BaseModel):
    events_total: int = 0
    events_loaded: int = 0
    events_missing: int = 0
    participants_total: int = 0
    unique_entities: int = 0
    has_minimum_network: bool = False
    fallback_reason: str | None = None


class SignalGraphResponse(BaseModel):
    signal: SignalGraphSignalOut
    pattern_story: SignalPatternStoryOut
    overview: SignalGraphOverviewOut
    timeline: list[SignalTimelineEventOut] = Field(default_factory=list)
    involved_entities: list[SignalInvolvedEntityProfileOut] = Field(default_factory=list)
    diagnostics: SignalGraphDiagnosticsOut
