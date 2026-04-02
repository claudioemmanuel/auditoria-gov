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
from shared.typologies.t11_spreadsheet_manipulation import T11SpreadsheetManipulationTypology
from shared.typologies.t12_directed_tender import T12DirectedTenderTypology
from shared.typologies.t13_conflict_of_interest import T13ConflictOfInterestTypology
from shared.typologies.t14_compound_favoritism import T14CompoundFavoritismTypology
from shared.typologies.t15_false_sole_source import T15FalseSoleSourceTypology
from shared.typologies.t16_budget_clientelism import T16BudgetClientelismTypology
from shared.typologies.t17_layered_money_laundering import T17LayeredMoneyLaunderingTypology
from shared.typologies.t18_illegal_position_accumulation import T18IllegalPositionAccumulationTypology
from shared.typologies.t19_bid_rotation import T19BidRotationTypology
from shared.typologies.t20_phantom_bidders import T20PhantomBidderTypology
from shared.typologies.t21_collusive_cluster import T21CollusiveClusterTypology
from shared.typologies.t22_political_favoritism import T22PoliticalFavoritismTypology
from shared.typologies.t23_bim_cost_overrun import T23BimCostOverrunTypology
from shared.typologies.t24_me_epp_quota_fraud import T24MeEppQuotaFraudTypology
from shared.typologies.t25_tcu_condemned import T25TCUCondemnedTypology
from shared.typologies.t26_state_penalty_mismatch import T26StatePenaltyMismatchTypology
from shared.typologies.t27_bndes_loan_nexus import T27BndesLoanNexusTypology
from shared.typologies.t28_judicial_precedent_warning import T28JudicialPrecedentWarningTypology

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
    "T11": T11SpreadsheetManipulationTypology,
    "T12": T12DirectedTenderTypology,
    "T13": T13ConflictOfInterestTypology,
    "T14": T14CompoundFavoritismTypology,
    "T15": T15FalseSoleSourceTypology,
    "T16": T16BudgetClientelismTypology,
    "T17": T17LayeredMoneyLaunderingTypology,
    "T18": T18IllegalPositionAccumulationTypology,
    "T19": T19BidRotationTypology,
    "T20": T20PhantomBidderTypology,
    "T21": T21CollusiveClusterTypology,
    "T22": T22PoliticalFavoritismTypology,
    "T23": T23BimCostOverrunTypology,
    "T24": T24MeEppQuotaFraudTypology,
    "T25": T25TCUCondemnedTypology,
    "T26": T26StatePenaltyMismatchTypology,
    "T27": T27BndesLoanNexusTypology,
    "T28": T28JudicialPrecedentWarningTypology,
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
