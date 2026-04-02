from shared.connectors.base import BaseConnector, SourceClassification
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
from shared.connectors.orcamento_bim import OrcamentoBIMConnector
from shared.connectors.tcu import TCUConnector
from shared.connectors.datajud import DataJudConnector
from shared.connectors.ibge import IBGEConnector

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
    "orcamento_bim": OrcamentoBIMConnector,
    "tcu": TCUConnector,
    "datajud": DataJudConnector,
    "ibge": IBGEConnector,
}


def get_connector(name: str) -> BaseConnector:
    """Factory to instantiate a connector by name."""
    alias_map = {
        "receita_federal_cnpj": "receita_cnpj",
    }
    resolved_name = alias_map.get(name, name)
    cls = ConnectorRegistry.get(resolved_name)
    if cls is None:
        raise ValueError(f"Unknown connector: {name}")
    return cls()
