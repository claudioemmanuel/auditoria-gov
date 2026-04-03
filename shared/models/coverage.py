from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


Status = Literal["ok", "warning", "stale", "error", "pending"]


class CoverageItem(BaseModel):
    connector: str
    job: str
    domain: str
    status: Status
    description: Optional[str] = None
    enabled_in_mvp: bool = False
    last_success_at: Optional[datetime] = None
    freshness_lag_hours: Optional[float] = None
    total_items: int = 0
    last_run_error: bool = False
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None


CoverageLayer = Literal["uf", "municipio"]
CoverageMetric = Literal["coverage", "freshness", "risk"]


class CoverageMapItem(BaseModel):
    code: str
    label: str
    layer: CoverageLayer
    event_count: int = 0
    signal_count: int = 0
    coverage_score: float = 0.0
    freshness_hours: Optional[float] = None
    risk_score: float = 0.0
    status: Status = "pending"


class CoverageMapResponse(BaseModel):
    layer: CoverageLayer
    metric: CoverageMetric
    date_ref: datetime
    generated_at: datetime
    items: list[CoverageMapItem]
