from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Iterable

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from openwatch_config.settings import settings
from openwatch_utils.logging import log
from openwatch_models.orm import Event
from openwatch_models.signals import RiskSignalOut


class BaseTypology(ABC):
    """Abstract base for all typology detectors."""

    @property
    @abstractmethod
    def id(self) -> str:
        """Typology code, e.g. 'T01'."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name."""
        ...

    @property
    @abstractmethod
    def required_domains(self) -> list[str]:
        """Data domains this typology needs (e.g. ['licitacao'])."""
        ...

    @property
    def required_fields(self) -> list[str]:
        """Event/entity fields required for this analysis."""
        return []

    @property
    def corruption_types(self) -> list[str]:
        """Legal corruption types covered (e.g. 'fraude_licitatoria', 'peculato').

        Aligned with legal-first doc types:
        - corrupcao_ativa, corrupcao_passiva, concussao, prevaricacao,
          peculato, lavagem, fraude_licitatoria, nepotismo_clientelismo
        """
        return []

    @property
    def spheres(self) -> list[str]:
        """Corruption spheres covered (politica, administrativa, privada, sistemica)."""
        return []

    @property
    def evidence_level(self) -> str:
        """Minimum evidence level: 'direct', 'indirect', 'proxy'."""
        return "indirect"

    @property
    def window_min_days(self) -> int:
        return settings.TYPOLOGY_WINDOW_MIN_DAYS

    @property
    def window_max_days(self) -> int:
        return settings.TYPOLOGY_WINDOW_MAX_DAYS

    async def resolve_window(self, session, required_domains: Iterable[str]) -> tuple[datetime, datetime]:
        """Resolve a data-aware analysis window bounded by configured min/max days."""
        window_end = datetime.now(timezone.utc)
        domains = [d for d in required_domains if d]
        if not domains:
            return window_end - timedelta(days=self.window_min_days), window_end
        if not isinstance(session, AsyncSession):
            window_start = window_end - timedelta(days=self.window_min_days)
            bounded_start = max(window_start, window_end - timedelta(days=self.window_max_days))
            return bounded_start, window_end

        stmt = (
            select(func.min(Event.occurred_at), func.max(Event.occurred_at))
            .where(Event.type.in_(domains))
        )
        result = await session.execute(stmt)
        try:
            min_dt, max_dt = result.one()
        except (AttributeError, TypeError, ValueError):
            window_start = window_end - timedelta(days=self.window_min_days)
            bounded_start = max(window_start, window_end - timedelta(days=self.window_max_days))
            return bounded_start, window_end

        candidate_end = max_dt or window_end
        if candidate_end.tzinfo is None:
            candidate_end = candidate_end.replace(tzinfo=timezone.utc)

        if min_dt is None:
            window_start = candidate_end - timedelta(days=self.window_min_days)
            bounded_start = max(window_start, candidate_end - timedelta(days=self.window_max_days))
            return bounded_start, candidate_end

        if min_dt.tzinfo is None:
            min_dt = min_dt.replace(tzinfo=timezone.utc)

        full_span_days = max(1, (candidate_end - min_dt).days)
        bounded_days = min(max(full_span_days, self.window_min_days), self.window_max_days)
        window_start = candidate_end - timedelta(days=bounded_days)

        log.debug(
            "typology.window_resolved",
            typology=self.id,
            domains=list(domains),
            available_days=full_span_days,
            bounded_days=bounded_days,
            window_start=window_start.isoformat(),
            window_end=candidate_end.isoformat(),
        )
        return window_start, candidate_end

    @abstractmethod
    async def run(self, session) -> list[RiskSignalOut]:
        """Execute typology detection and return risk signals."""
        ...
