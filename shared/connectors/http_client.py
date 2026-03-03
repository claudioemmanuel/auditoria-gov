"""Shared async HTTP client for all connectors."""

import httpx

from shared.config import settings

# Timeouts: 30s connect, 60s read
DEFAULT_TIMEOUT = httpx.Timeout(connect=30.0, read=60.0, write=30.0, pool=30.0)
DEFAULT_PAGE_SIZE = 100


def portal_transparencia_client() -> httpx.AsyncClient:
    """HTTP client for Portal da Transparência API."""
    return httpx.AsyncClient(
        base_url="https://api.portaldatransparencia.gov.br/api-de-dados",
        headers={"chave-api-dados": settings.PORTAL_TRANSPARENCIA_TOKEN},
        timeout=DEFAULT_TIMEOUT,
    )


def compras_gov_client() -> httpx.AsyncClient:
    """HTTP client for Compras.gov.br open-data API.

    Docs: https://compras.dados.gov.br/docs/home.html
    Module-based URL structure: /{module}/v1/{method}.json
    """
    return httpx.AsyncClient(
        base_url="https://compras.dados.gov.br",
        headers={"Accept": "application/json"},
        timeout=DEFAULT_TIMEOUT,
    )


def comprasnet_contratos_client() -> httpx.AsyncClient:
    """HTTP client for ComprasNet Contratos (open-data, via compras.dados.gov.br).

    The old contratos.comprasnet.gov.br/api requires OAuth2 and is not public.
    We use the open-data contracts endpoint at compras.dados.gov.br instead.
    Docs: https://compras.dados.gov.br/docs/contratos.html
    """
    return httpx.AsyncClient(
        base_url="https://compras.dados.gov.br",
        headers={"Accept": "application/json"},
        timeout=DEFAULT_TIMEOUT,
    )


def pncp_client() -> httpx.AsyncClient:
    """HTTP client for PNCP API."""
    return httpx.AsyncClient(
        base_url="https://pncp.gov.br/api/consulta/v1",
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
    return httpx.AsyncClient(
        base_url=base,
        headers={"Accept": "application/json"},
        timeout=DEFAULT_TIMEOUT,
    )


def camara_client() -> httpx.AsyncClient:
    """HTTP client for Câmara dos Deputados API."""
    return httpx.AsyncClient(
        base_url="https://dadosabertos.camara.leg.br/api/v2",
        headers={"Accept": "application/json"},
        timeout=DEFAULT_TIMEOUT,
    )


def senado_client() -> httpx.AsyncClient:
    """HTTP client for Senado Federal API."""
    return httpx.AsyncClient(
        base_url="https://legis.senado.leg.br/dadosabertos",
        headers={"Accept": "application/json"},
        timeout=DEFAULT_TIMEOUT,
    )


def senado_ceaps_client() -> httpx.AsyncClient:
    """HTTP client for senator expenses (CEAPS) via Codante API.

    The official Senado /senador/lista/ceaps/{ano} endpoint returns 404.
    Codante aggregates the same CEAPS data at a working REST endpoint.
    Docs: https://docs.apis.codante.io/gastos-senadores
    """
    return httpx.AsyncClient(
        base_url="https://apis.codante.io/senator-expenses",
        headers={"Accept": "application/json"},
        timeout=DEFAULT_TIMEOUT,
    )
