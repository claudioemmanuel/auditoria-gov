"""Domain whitelist enforcement for outbound HTTP requests.

All connectors must validate their target URLs against government TLDs
or pre-approved exceptions before making HTTP calls. This prevents
data ingestion from unauthorized or non-authoritative sources.
"""

from dataclasses import dataclass
from datetime import date
from urllib.parse import urlparse

GOVERNMENT_TLDS: frozenset[str] = frozenset({
    ".gov.br",
    ".jus.br",
    ".leg.br",
    ".mil.br",
    ".mp.br",
    ".def.br",
})


@dataclass(frozen=True)
class DomainException:
    """A controlled exception to the government-only domain rule."""

    domain: str
    justification: str
    max_veracity: float  # 0.0–1.0 ceiling for veracity score
    approved_date: date
    review_by: date


DOMAIN_EXCEPTIONS: dict[str, DomainException] = {
    "api.queridodiario.ok.org.br": DomainException(
        domain="api.queridodiario.ok.org.br",
        justification=(
            "Querido Diário is an Open Knowledge Brasil project that aggregates "
            "municipal gazettes. No official federal API exists for this data."
        ),
        max_veracity=0.85,
        approved_date=date(2026, 3, 4),
        review_by=date(2026, 9, 4),  # 6-month review
    ),
    "dados.tcerj.tc.br": DomainException(
        domain="dados.tcerj.tc.br",
        justification=(
            "TCE-RJ (Tribunal de Contas do Estado do Rio de Janeiro) publishes "
            "open data on municipal procurement, contracts, and penalties. "
            "Domain ends in .tc.br, not a standard government TLD."
        ),
        max_veracity=0.90,
        approved_date=date(2026, 1, 10),
        review_by=date(2027, 1, 10),  # 6-month review
    ),
    "brasilapi.com.br": DomainException(
        domain="brasilapi.com.br",
        justification=(
            "BrasilAPI is a public mirror/wrapper that republishes official "
            "Brazilian government registration data, including CNPJ records."
        ),
        max_veracity=0.78,
        approved_date=date(2026, 1, 10),
        review_by=date(2027, 1, 10),  # 6-month review
    ),
}


class DomainNotAllowedError(Exception):
    """Raised when a URL targets a domain outside the whitelist."""

    def __init__(self, domain: str, url: str) -> None:
        self.domain = domain
        self.url = url
        super().__init__(
            f"Domain '{domain}' is not in the government whitelist and has no "
            f"approved exception. URL: {url}"
        )


def _extract_domain(url: str) -> str:
    """Extract the hostname from a URL."""
    parsed = urlparse(url)
    return (parsed.hostname or "").lower()


def is_government_domain(url: str) -> bool:
    """Check whether a URL belongs to a Brazilian government TLD."""
    domain = _extract_domain(url)
    return any(domain.endswith(tld) for tld in GOVERNMENT_TLDS)


def validate_domain(url: str) -> float:
    """Validate a URL against the domain whitelist.

    Returns the veracity ceiling for the domain:
    - 1.0 for government domains
    - exception.max_veracity for approved exceptions
    - Raises DomainNotAllowedError for all other domains

    Args:
        url: The base URL to validate.

    Returns:
        Veracity ceiling (float between 0 and 1).

    Raises:
        DomainNotAllowedError: If the domain is not whitelisted.
    """
    domain = _extract_domain(url)

    # Government domains pass with full veracity
    if any(domain.endswith(tld) for tld in GOVERNMENT_TLDS):
        return 1.0

    # Check controlled exceptions
    exception = DOMAIN_EXCEPTIONS.get(domain)
    if exception is not None:
        return exception.max_veracity

    raise DomainNotAllowedError(domain=domain, url=url)
