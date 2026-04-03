from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from openwatch_models.canonical import NormalizeResult
from openwatch_models.raw import RawItem


class SourceClassification(str, Enum):
    """Classification of a data source for signal generation purposes."""
    FULL_SOURCE = "full_source"
    """Source can independently generate risk signals."""
    ENRICHMENT_ONLY = "enrichment_only"
    """Source can only enrich existing signals, never create signals independently.
    Used for non-government sources like OpenSanctions that pass a DomainException."""


@dataclass
class RateLimitPolicy:
    requests_per_second: int = 5
    burst: int = 10


@dataclass
class JobSpec:
    name: str
    description: str
    domain: str
    supports_incremental: bool = True
    # Opt-in for automated ingest schedules.
    enabled: bool = False
    default_params: dict = field(default_factory=dict)


class BaseConnector(ABC):
    """Abstract base for all data source connectors."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Connector identifier."""
        ...

    @abstractmethod
    def list_jobs(self) -> list[JobSpec]:
        """Return all available ingestion jobs."""
        ...

    @abstractmethod
    async def fetch(
        self,
        job: JobSpec,
        cursor: Optional[str] = None,
        params: Optional[dict] = None,
    ) -> tuple[list[RawItem], Optional[str]]:
        """Fetch raw data. Returns (items, next_cursor)."""
        ...

    @abstractmethod
    def normalize(
        self,
        job: JobSpec,
        raw_items: list[RawItem],
        params: Optional[dict] = None,
    ) -> NormalizeResult:
        """Normalize raw items into canonical models."""
        ...

    @property
    def classification(self) -> SourceClassification:
        """Source classification for signal generation gating."""
        return SourceClassification.FULL_SOURCE

    def rate_limit_policy(self) -> RateLimitPolicy:
        """Return rate limiting policy for this connector's API."""
        return RateLimitPolicy()
