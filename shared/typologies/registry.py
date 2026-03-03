from shared.typologies.base import BaseTypology
from shared.typologies.t01_concentration import T01ConcentrationTypology
from shared.typologies.t02_low_competition import T02LowCompetitionTypology
from shared.typologies.t03_splitting import T03SplittingTypology
from shared.typologies.t04_amendments_outlier import T04AmendmentsOutlierTypology
from shared.typologies.t05_price_outlier import T05PriceOutlierTypology
from shared.typologies.t06_shell_company_proxy import T06ShellCompanyProxyTypology
from shared.typologies.t07_cartel_network import T07CartelNetworkTypology
from shared.typologies.t08_sanctions_mismatch import T08SanctionsMismatchTypology
from shared.typologies.t09_ghost_payroll_proxy import T09GhostPayrollProxyTypology
from shared.typologies.t10_outsourcing_parallel_payroll import T10OutsourcingParallelPayrollTypology

TypologyRegistry: dict[str, type[BaseTypology]] = {
    "T01": T01ConcentrationTypology,
    "T02": T02LowCompetitionTypology,
    "T03": T03SplittingTypology,
    "T04": T04AmendmentsOutlierTypology,
    "T05": T05PriceOutlierTypology,
    "T06": T06ShellCompanyProxyTypology,
    "T07": T07CartelNetworkTypology,
    "T08": T08SanctionsMismatchTypology,
    "T09": T09GhostPayrollProxyTypology,
    "T10": T10OutsourcingParallelPayrollTypology,
}


def get_all_typologies() -> list[BaseTypology]:
    """Instantiate and return all registered typologies."""
    return [cls() for cls in TypologyRegistry.values()]


def get_typology(code: str) -> BaseTypology:
    """Get a single typology by code."""
    cls = TypologyRegistry.get(code)
    if cls is None:
        raise ValueError(f"Unknown typology: {code}")
    return cls()
