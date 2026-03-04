"""Source veracity scoring model.

Each data source receives a weighted composite score based on five criteria:
  - Government domain (40%)
  - Legal authority (25%)
  - Public availability (15%)
  - Official API documented (10%)
  - Metadata & traceability (10%)

Labels:
  official  >= 0.95
  high      >= 0.85
  acceptable >= 0.70
  low       < 0.70
"""

from dataclasses import dataclass
from enum import Enum


class DomainTier(Enum):
    GOVERNMENT = "government"
    EXCEPTION = "exception"


@dataclass(frozen=True)
class SourceVeracityProfile:
    """Veracity profile for a single connector:job pair."""

    government_domain: float  # 0.0–1.0
    legal_authority: float
    public_availability: float
    official_api_documented: float
    metadata_traceability: float
    domain_tier: DomainTier

    @property
    def composite_score(self) -> float:
        return round(
            self.government_domain * 0.40
            + self.legal_authority * 0.25
            + self.public_availability * 0.15
            + self.official_api_documented * 0.10
            + self.metadata_traceability * 0.10,
            4,
        )

    @property
    def veracity_label(self) -> str:
        score = self.composite_score
        if score >= 0.95:
            return "official"
        if score >= 0.85:
            return "high"
        if score >= 0.70:
            return "acceptable"
        return "low"


# ── Pre-computed profiles for all connector:job pairs ──────────────────

_GOV = DomainTier.GOVERNMENT
_EXC = DomainTier.EXCEPTION

# Portal da Transparência — CGU-managed, .gov.br, full legal backing
_PT_PROFILE = SourceVeracityProfile(
    government_domain=1.0,
    legal_authority=1.0,
    public_availability=1.0,
    official_api_documented=1.0,
    metadata_traceability=0.95,
    domain_tier=_GOV,
)

# Compras.gov.br — federal procurement, .gov.br
_COMPRAS_PROFILE = SourceVeracityProfile(
    government_domain=1.0,
    legal_authority=1.0,
    public_availability=1.0,
    official_api_documented=0.90,
    metadata_traceability=0.90,
    domain_tier=_GOV,
)

# ComprasNet Contratos — same domain as compras.gov
_CNET_PROFILE = SourceVeracityProfile(
    government_domain=1.0,
    legal_authority=1.0,
    public_availability=1.0,
    official_api_documented=0.85,
    metadata_traceability=0.85,
    domain_tier=_GOV,
)

# PNCP — official procurement portal, .gov.br
_PNCP_PROFILE = SourceVeracityProfile(
    government_domain=1.0,
    legal_authority=1.0,
    public_availability=1.0,
    official_api_documented=0.95,
    metadata_traceability=0.90,
    domain_tier=_GOV,
)

# TransfereGov — official transfers, .gov.br
_TRANSFEREGOV_PROFILE = SourceVeracityProfile(
    government_domain=1.0,
    legal_authority=1.0,
    public_availability=1.0,
    official_api_documented=0.90,
    metadata_traceability=0.85,
    domain_tier=_GOV,
)

# Câmara dos Deputados — .leg.br, legislative open data
_CAMARA_PROFILE = SourceVeracityProfile(
    government_domain=1.0,
    legal_authority=1.0,
    public_availability=1.0,
    official_api_documented=1.0,
    metadata_traceability=0.90,
    domain_tier=_GOV,
)

# Senado Federal — .leg.br, official API
_SENADO_PROFILE = SourceVeracityProfile(
    government_domain=1.0,
    legal_authority=1.0,
    public_availability=1.0,
    official_api_documented=0.85,
    metadata_traceability=0.85,
    domain_tier=_GOV,
)

# TSE — .gov.br, bulk download (not API), strong legal authority
_TSE_PROFILE = SourceVeracityProfile(
    government_domain=1.0,
    legal_authority=1.0,
    public_availability=1.0,
    official_api_documented=0.70,
    metadata_traceability=0.80,
    domain_tier=_GOV,
)

# Receita Federal — .gov.br, bulk CNPJ data
_RECEITA_PROFILE = SourceVeracityProfile(
    government_domain=1.0,
    legal_authority=1.0,
    public_availability=1.0,
    official_api_documented=0.70,
    metadata_traceability=0.80,
    domain_tier=_GOV,
)

# Querido Diário — exception domain, community project
_QD_PROFILE = SourceVeracityProfile(
    government_domain=0.0,
    legal_authority=0.50,
    public_availability=1.0,
    official_api_documented=0.90,
    metadata_traceability=0.70,
    domain_tier=_EXC,
)


SOURCE_VERACITY_REGISTRY: dict[str, SourceVeracityProfile] = {
    # Portal da Transparência (8 jobs)
    "portal_transparencia:pt_sancoes_ceis_cnep": _PT_PROFILE,
    "portal_transparencia:pt_servidores_remuneracao": _PT_PROFILE,
    "portal_transparencia:pt_viagens": _PT_PROFILE,
    "portal_transparencia:pt_cartao_pagamento": _PT_PROFILE,
    "portal_transparencia:pt_despesas_execucao": _PT_PROFILE,
    "portal_transparencia:pt_beneficios": _PT_PROFILE,
    "portal_transparencia:pt_emendas": _PT_PROFILE,
    "portal_transparencia:pt_convenios_transferencias": _PT_PROFILE,
    # Compras.gov (3 jobs)
    "compras_gov:compras_licitacoes_by_period": _COMPRAS_PROFILE,
    "compras_gov:compras_catalogo_catmat_full": _COMPRAS_PROFILE,
    "compras_gov:compras_catalogo_catser_full": _COMPRAS_PROFILE,
    # ComprasNet Contratos (1 job)
    "comprasnet_contratos:cnet_contracts": _CNET_PROFILE,
    # PNCP (3 jobs)
    "pncp:pncp_contracting_notices": _PNCP_PROFILE,
    "pncp:pncp_contracts": _PNCP_PROFILE,
    "pncp:pncp_arp": _PNCP_PROFILE,
    # TransfereGov (2 jobs)
    "transferegov:transferegov_ted": _TRANSFEREGOV_PROFILE,
    "transferegov:transferegov_transferencias_especiais": _TRANSFEREGOV_PROFILE,
    # Câmara (3 jobs)
    "camara:camara_deputados": _CAMARA_PROFILE,
    "camara:camara_despesas_cota": _CAMARA_PROFILE,
    "camara:camara_orgaos": _CAMARA_PROFILE,
    # Senado (2 jobs)
    "senado:senado_senadores": _SENADO_PROFILE,
    "senado:senado_ceaps": _SENADO_PROFILE,
    # TSE (4 jobs)
    "tse:tse_candidatos": _TSE_PROFILE,
    "tse:tse_bens_candidatos": _TSE_PROFILE,
    "tse:tse_receitas_candidatos": _TSE_PROFILE,
    "tse:tse_despesas_candidatos": _TSE_PROFILE,
    # Receita Federal (3 jobs)
    "receita_cnpj:rf_empresas": _RECEITA_PROFILE,
    "receita_cnpj:rf_socios": _RECEITA_PROFILE,
    "receita_cnpj:rf_estabelecimentos": _RECEITA_PROFILE,
    # Querido Diário (1 job)
    "querido_diario:qd_gazettes": _QD_PROFILE,
}
