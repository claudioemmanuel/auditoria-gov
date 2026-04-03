import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from openwatch_models.graph import CaseGraphResponse, SignalGraphResponse
from openwatch_models.signals import SignalSeverity


class RadarV2TotalsOut(BaseModel):
    signals: int = 0
    cases: int = 0


class RadarV2SeverityCountsOut(BaseModel):
    low: int = 0
    medium: int = 0
    high: int = 0
    critical: int = 0


class RadarV2TypologyCountOut(BaseModel):
    code: str
    name: str
    count: int


class RadarV2SummaryResponse(BaseModel):
    snapshot_at: datetime
    totals: RadarV2TotalsOut
    severity_counts: RadarV2SeverityCountsOut
    typology_counts: list[RadarV2TypologyCountOut] = Field(default_factory=list)
    active_filters_count: int = 0


class RadarV2SignalListItemOut(BaseModel):
    id: uuid.UUID
    typology_code: str
    typology_name: str
    severity: SignalSeverity
    confidence: float
    title: str
    summary: Optional[str] = None
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    created_at: datetime
    event_count: int = 0
    entity_count: int = 0
    has_graph: bool = False


class RadarV2SignalListResponse(BaseModel):
    items: list[RadarV2SignalListItemOut] = Field(default_factory=list)
    total: int
    offset: int
    limit: int


class RadarV2CaseListItemOut(BaseModel):
    id: uuid.UUID
    title: str
    status: str
    severity: SignalSeverity
    summary: Optional[str] = None
    case_type: Optional[str] = None
    signal_count: int = 0
    entity_count: int = 0
    typology_codes: list[str] = Field(default_factory=list)
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    created_at: datetime


class RadarV2CaseListResponse(BaseModel):
    items: list[RadarV2CaseListItemOut] = Field(default_factory=list)
    total: int
    offset: int
    limit: int


class RadarV2SignalPreviewResponse(BaseModel):
    signal: dict
    graph: SignalGraphResponse
    evidence: dict


class RadarV2CasePreviewResponse(BaseModel):
    case: dict
    graph: CaseGraphResponse
    top_signals: list[dict] = Field(default_factory=list)


class RadarV2CoverageSummaryOut(BaseModel):
    apt_count: int = 0
    with_signals_30d: int = 0
    blocked_count: int = 0
    total_typologies: int = 0


class RadarV2CoverageResponse(BaseModel):
    summary: RadarV2CoverageSummaryOut
    items: list[dict] = Field(default_factory=list)
