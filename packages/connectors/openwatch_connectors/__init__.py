from openwatch_connectors.base import BaseConnector, SourceClassification
from openwatch_connectors.portal_transparencia import PortalTransparenciaConnector
from openwatch_connectors.compras_gov import ComprasGovConnector
from openwatch_connectors.comprasnet_contratos import ComprasNetContratosConnector
from openwatch_connectors.pncp import PNCPConnector
from openwatch_connectors.transferegov import TransfereGovConnector
from openwatch_connectors.camara import CamaraConnector
from openwatch_connectors.senado import SenadoConnector
from openwatch_connectors.tse import TSEConnector
from openwatch_connectors.receita_cnpj import ReceitaCNPJConnector
from openwatch_connectors.querido_diario import QueridoDiarioConnector
from openwatch_connectors.orcamento_bim import OrcamentoBIMConnector
from openwatch_connectors.tcu import TCUConnector
from openwatch_connectors.datajud import DataJudConnector
from openwatch_connectors.ibge import IBGEConnector
from openwatch_connectors.jurisprudencia import JurisprudenciaConnector
from openwatch_connectors.tce_rj import TCERJConnector
from openwatch_connectors.tce_sp import TCESPConnector
from openwatch_connectors.bacen import BacenConnector
from openwatch_connectors.bndes import BNDESConnector

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
    "jurisprudencia": JurisprudenciaConnector,
    "tce_rj": TCERJConnector,
    "tce_sp": TCESPConnector,
    "bacen": BacenConnector,
    "bndes": BNDESConnector,
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
