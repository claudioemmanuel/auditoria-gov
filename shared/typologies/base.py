from abc import ABC, abstractmethod

from shared.models.signals import RiskSignalOut


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

    @abstractmethod
    async def run(self, session) -> list[RiskSignalOut]:
        """Execute typology detection and return risk signals."""
        ...
