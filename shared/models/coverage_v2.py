import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

from shared.models.coverage import CoverageMapItem, CoverageMetric


CoveragePipelineStatus = Literal["done", "processing", "warning", "error", "pending"]
CoverageOverallStatus = Literal["healthy", "attention", "blocked"]
CoverageSourceStatus = Literal["ok", "warning", "stale", "error", "pending"]
CoverageMapLayer = Literal["uf", "municipio"]


class CoverageV2StatusCounts(BaseModel):
    ok: int = 0
    warning: int = 0
    stale: int = 0
    error: int = 0
    pending: int = 0


class CoverageV2RuntimeTotals(BaseModel):
    running: int = 0
    stuck: int = 0
    failed_or_stuck: int = 0


class CoverageV2Totals(BaseModel):
    connectors: int = 0
    jobs: int = 0
    jobs_enabled: int = 0
    signals_total: int = 0
    status_counts: CoverageV2StatusCounts
    runtime: CoverageV2RuntimeTotals


class CoverageV2PipelineStage(BaseModel):
    code: str
    label: str
    status: CoveragePipelineStatus
    reason: str


class CoverageV2PipelineSummary(BaseModel):
    overall_status: CoverageOverallStatus
    stages: list[CoverageV2PipelineStage] = Field(default_factory=list)


class CoverageV2ScheduleWindow(BaseModel):
    job_code: str
    window: str


class CoverageV2SummaryResponse(BaseModel):
    snapshot_at: datetime
    totals: CoverageV2Totals
    pipeline: CoverageV2PipelineSummary
    schedule_windows_brt: list[CoverageV2ScheduleWindow] = Field(default_factory=list)


class CoverageV2SourceRuntime(BaseModel):
    running_jobs: int = 0
    stuck_jobs: int = 0
    error_jobs: int = 0


class CoverageV2SourceItem(BaseModel):
    connector: str
    connector_label: str
    job_count: int
    enabled_job_count: int
    worst_status: CoverageSourceStatus
    status_counts: CoverageV2StatusCounts
    runtime: CoverageV2SourceRuntime
    last_success_at: Optional[datetime] = None
    max_freshness_lag_hours: Optional[float] = None


class CoverageV2SourcesResponse(BaseModel):
    items: list[CoverageV2SourceItem] = Field(default_factory=list)
    total: int
    offset: int
    limit: int


class CoverageV2LatestRun(BaseModel):
    id: uuid.UUID
    status: str
    is_stuck: bool = False
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    items_fetched: int = 0
    items_normalized: int = 0
    error_message: Optional[str] = None


class CoverageV2SourcePreviewConnector(BaseModel):
    connector: str
    connector_label: str
    worst_status: CoverageSourceStatus
    job_count: int
    enabled_job_count: int
    status_counts: CoverageV2StatusCounts


class CoverageV2SourcePreviewJob(BaseModel):
    job: str
    domain: str
    description: Optional[str] = None
    enabled_in_mvp: bool = False
    status: CoverageSourceStatus
    total_items: int = 0
    last_success_at: Optional[datetime] = None
    freshness_lag_hours: Optional[float] = None
    latest_run: Optional[CoverageV2LatestRun] = None


class CoverageV2SourcePreviewResponse(BaseModel):
    connector: CoverageV2SourcePreviewConnector
    jobs: list[CoverageV2SourcePreviewJob] = Field(default_factory=list)
    recent_runs: list[CoverageV2LatestRun] = Field(default_factory=list)
    insights: list[str] = Field(default_factory=list)


class CoverageV2MapNational(BaseModel):
    regions_with_data: int = 0
    regions_without_data: int = 0
    total_events: int = 0
    total_signals: int = 0


class CoverageV2MapResponse(BaseModel):
    layer: CoverageMapLayer
    metric: CoverageMetric
    generated_at: datetime
    date_ref: datetime
    national: CoverageV2MapNational
    items: list[CoverageMapItem] = Field(default_factory=list)


class CoverageV2AnalyticsSummary(BaseModel):
    total_typologies: int = 0
    apt_count: int = 0
    blocked_count: int = 0
    with_signals_30d: int = 0


class CoverageV2AnalyticsResponse(BaseModel):
    summary: CoverageV2AnalyticsSummary
    items: list[dict] = Field(default_factory=list)


class CoverageV2RunFieldProfile(BaseModel):
    key: str
    present_count: int
    coverage_pct: float
    detected_types: list[str] = Field(default_factory=list)
    examples: list[object] = Field(default_factory=list)


class CoverageV2RunSampleRecord(BaseModel):
    raw_id: str
    created_at: Optional[str] = None
    preview: dict
    raw_data: dict


class CoverageV2RunDetailResponse(BaseModel):
    run: dict
    job: dict
    summary: dict
    field_profile: list[CoverageV2RunFieldProfile] = Field(default_factory=list)
    samples: list[CoverageV2RunSampleRecord] = Field(default_factory=list)
