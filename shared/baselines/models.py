from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


MIN_SAMPLE_SIZE = 30


class BaselineType(str, Enum):
    PRICE_BY_ITEM = "PRICE_BY_ITEM"
    PARTICIPANTS_PER_PROCUREMENT = "PARTICIPANTS_PER_PROCUREMENT"
    HHI_DISTRIBUTION = "HHI_DISTRIBUTION"
    AMENDMENT_DISTRIBUTION = "AMENDMENT_DISTRIBUTION"
    CONTRACT_DURATION = "CONTRACT_DURATION"


class BaselineMetrics(BaseModel):
    """Percentile-based metrics for a baseline distribution."""

    baseline_type: BaselineType
    scope_key: str
    sample_size: int
    mean: float
    median: float
    std: float
    p5: float
    p10: float
    p25: float
    p75: float
    p90: float
    p95: float
    p99: float
    min_val: float = Field(alias="min")
    max_val: float = Field(alias="max")

    model_config = {"populate_by_name": True}
