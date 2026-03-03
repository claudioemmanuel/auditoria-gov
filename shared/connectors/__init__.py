from shared.connectors.base import BaseConnector
from shared.connectors.portal_transparencia import PortalTransparenciaConnector
from shared.connectors.compras_gov import ComprasGovConnector
from shared.connectors.comprasnet_contratos import ComprasNetContratosConnector
from shared.connectors.pncp import PNCPConnector
from shared.connectors.transferegov import TransfereGovConnector
from shared.connectors.camara import CamaraConnector
from shared.connectors.senado import SenadoConnector
from shared.connectors.tse import TSEConnector
from shared.connectors.receita_cnpj import ReceitaCNPJConnector
from shared.connectors.querido_diario import QueridoDiarioConnector

ConnectorRegistry: dict[str, type[BaseConnector]] = {
    "portal_transparencia": PortalTransparenciaConnector,
    "compras_gov": ComprasGovConnector,
    "comprasnet_contratos": ComprasNetContratosConnector,
    "pncp": PNCPConnector,
    "transferegov": TransfereGovConnector,
    "camara": CamaraConnector,
    "senado": SenadoConnector,
    "tse": TSEConnector,
    "receita_cnpj": ReceitaCNPJConnector,
    "querido_diario": QueridoDiarioConnector,
}


def get_connector(name: str) -> BaseConnector:
    """Factory to instantiate a connector by name."""
    cls = ConnectorRegistry.get(name)
    if cls is None:
        raise ValueError(f"Unknown connector: {name}")
    return cls()
