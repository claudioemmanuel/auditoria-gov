from datetime import datetime
from typing import Literal

from pydantic import BaseModel

Status = Literal["ok", "warning", "stale", "error", "pending"]


class CoverageItem(BaseModel):
    connector: str
    job: str
    domain: str
    status: Status
    description: str | None = None
    enabled_in_mvp: bool = False
    last_success_at: datetime | None = None
    freshness_lag_hours: float | None = None
    total_items: int = 0
    last_run_error: bool = False
    period_start: datetime | None = None
    period_end: datetime | None = None


CoverageLayer = Literal["uf", "municipio"]
CoverageMetric = Literal["coverage", "freshness", "risk"]


class CoverageMapItem(BaseModel):
    code: str
    label: str
    layer: CoverageLayer
    event_count: int = 0
    signal_count: int = 0
    coverage_score: float = 0.0
    freshness_hours: float | None = None
    risk_score: float = 0.0
    status: Status = "pending"


class CoverageMapResponse(BaseModel):
    layer: CoverageLayer
    metric: CoverageMetric
    date_ref: datetime
    generated_at: datetime
    items: list[CoverageMapItem]
