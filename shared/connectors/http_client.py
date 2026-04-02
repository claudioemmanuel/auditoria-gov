"""Shared async HTTP client for all connectors."""

import httpx

from shared.config import settings
from shared.connectors.domain_guard import validate_domain

# Timeouts: 30s connect, 60s read
DEFAULT_TIMEOUT = httpx.Timeout(connect=30.0, read=60.0, write=30.0, pool=30.0)
PORTAL_TIMEOUT = httpx.Timeout(connect=30.0, read=120.0, write=30.0, pool=30.0)
DEFAULT_PAGE_SIZE = 100


def _guarded_client(base_url: str, **kwargs: object) -> httpx.AsyncClient:
    """Create an HTTP client after validating the base URL against the domain whitelist.

    Raises DomainNotAllowedError if the domain is not a government TLD
    and has no approved exception.
    """
    validate_domain(base_url)
    return httpx.AsyncClient(base_url=base_url, **kwargs)


def portal_transparencia_client() -> httpx.AsyncClient:
    """HTTP client for Portal da Transparência API."""
    return _guarded_client(
        "https://api.portaldatransparencia.gov.br/api-de-dados",
        headers={"chave-api-dados": settings.PORTAL_TRANSPARENCIA_TOKEN},
        timeout=PORTAL_TIMEOUT,
    )


def compras_gov_client() -> httpx.AsyncClient:
    """HTTP client for Compras.gov.br open-data API.

    Docs: https://compras.dados.gov.br/docs/home.html
    Module-based URL structure: /{module}/v1/{method}.json
    """
    return _guarded_client(
        "https://compras.dados.gov.br",
        headers={"Accept": "application/json"},
        timeout=DEFAULT_TIMEOUT,
    )


def comprasnet_contratos_client() -> httpx.AsyncClient:
    """HTTP client for ComprasNet Contratos (open-data, via compras.dados.gov.br).

    The old contratos.comprasnet.gov.br/api requires OAuth2 and is not public.
    We use the open-data contracts endpoint at compras.dados.gov.br instead.
    Docs: https://compras.dados.gov.br/docs/contratos.html
    """
    return _guarded_client(
        "https://compras.dados.gov.br",
        headers={"Accept": "application/json"},
        timeout=DEFAULT_TIMEOUT,
    )


def pncp_client() -> httpx.AsyncClient:
    """HTTP client for PNCP API."""
    return _guarded_client(
        "https://pncp.gov.br/api/consulta/v1",
        headers={"Accept": "application/json"},
        timeout=DEFAULT_TIMEOUT,
    )


def transferegov_client(module: str = "") -> httpx.AsyncClient:
    """HTTP client for Transfere.gov.br open-data API (PostgREST).

    APIs are module-specific:
      - /transferenciasespeciais/
      - /ted/
      - /fundoafundo/
    Docs: https://docs.api.transferegov.gestao.gov.br/{module}/
    """
    base = f"https://api.transferegov.gestao.gov.br/{module}" if module else "https://api.transferegov.gestao.gov.br"
    return _guarded_client(
        base,
        headers={"Accept": "application/json"},
        timeout=DEFAULT_TIMEOUT,
    )


def camara_client() -> httpx.AsyncClient:
    """HTTP client for Câmara dos Deputados API."""
    return _guarded_client(
        "https://dadosabertos.camara.leg.br/api/v2",
        headers={"Accept": "application/json"},
        timeout=DEFAULT_TIMEOUT,
    )


def senado_client() -> httpx.AsyncClient:
    """HTTP client for Senado Federal API."""
    return _guarded_client(
        "https://legis.senado.leg.br/dadosabertos",
        headers={"Accept": "application/json"},
        timeout=DEFAULT_TIMEOUT,
    )


def tcu_contas_client() -> httpx.AsyncClient:
    """HTTP client for TCU contas API (inidoneos, inabilitados)."""
    return _guarded_client(
        "https://contas.tcu.gov.br",
        headers={"Accept": "application/json"},
        timeout=DEFAULT_TIMEOUT,
    )


def tcu_dados_client() -> httpx.AsyncClient:
    """HTTP client for TCU dados abertos API (acordaos)."""
    return _guarded_client(
        "https://dados-abertos.apps.tcu.gov.br",
        headers={"Accept": "application/json"},
        timeout=DEFAULT_TIMEOUT,
    )


def ibge_client() -> httpx.AsyncClient:
    """HTTP client for IBGE open-data API (servicodados.ibge.gov.br)."""
    return _guarded_client(
        "https://servicodados.ibge.gov.br/api",
        headers={"Accept": "application/json"},
        timeout=DEFAULT_TIMEOUT,
    )


def jurisprudencia_stf_client() -> httpx.AsyncClient:
    """HTTP client for STF Jurisprudência search API."""
    return _guarded_client(
        "https://jurisprudencia.stf.jus.br",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "OpenWatch/1.0 (https://github.com/claudioemmanuel/openwatch)",
        },
        timeout=DEFAULT_TIMEOUT,
    )


def tce_rj_client() -> httpx.AsyncClient:
    """HTTP client for TCE-RJ open-data API (dados.tcerj.tc.br)."""
    return _guarded_client(
        "https://dados.tcerj.tc.br/api/v1",
        headers={"Accept": "application/json"},
        timeout=DEFAULT_TIMEOUT,
    )


def bacen_client() -> httpx.AsyncClient:
    """HTTP client for Banco Central do Brasil SGS time-series API."""
    return _guarded_client(
        "https://api.bcb.gov.br",
        headers={"Accept": "application/json"},
        timeout=DEFAULT_TIMEOUT,
    )


def bndes_client() -> httpx.AsyncClient:
    """HTTP client for BNDES open-data CKAN API."""
    return _guarded_client(
        "https://dadosabertos.bndes.gov.br/api/3/action",
        headers={"Accept": "application/json"},
        timeout=DEFAULT_TIMEOUT,
    )


def datajud_client() -> httpx.AsyncClient:
    """HTTP client for DataJud (CNJ) public Elasticsearch API.

    Auth is optional: if DATAJUD_API_KEY is set it is sent as
    'APIKey {key}'; otherwise the header is omitted (public, rate-limited).
    """
    import os

    headers: dict[str, str] = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    key = os.environ.get("DATAJUD_API_KEY", "")
    if key:
        headers["Authorization"] = f"APIKey {key}"
    return _guarded_client(
        "https://api-publica.datajud.cnj.jus.br",
        headers=headers,
        timeout=DEFAULT_TIMEOUT,
    )


def tce_sp_client() -> httpx.AsyncClient:
    """HTTP client for TCE-SP (Tribunal de Contas do Estado de São Paulo)."""
    return _guarded_client(
        "https://transparencia.tce.sp.gov.br/api/json",
        headers={"Accept": "application/json"},
        timeout=DEFAULT_TIMEOUT,
    )
