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

# BrasilAPI CNPJ — non-government mirror/wrapper of official sources
_BRASILAPI_CNPJ_PROFILE = SourceVeracityProfile(
    government_domain=0.0,
    legal_authority=0.70,
    public_availability=1.0,
    official_api_documented=0.90,
    metadata_traceability=0.75,
    domain_tier=_EXC,
)

# Orçamento BIM (file-backed deterministic government dataset).
_ORCAMENTO_BIM_PROFILE = SourceVeracityProfile(
    government_domain=1.0,
    legal_authority=0.90,
    public_availability=0.90,
    official_api_documented=0.60,
    metadata_traceability=0.90,
    domain_tier=_GOV,
)

# TCU (Tribunal de Contas da União) — highest legal authority for public spending audits
_TCU_PROFILE = SourceVeracityProfile(
    government_domain=1.0,
    legal_authority=1.0,
    public_availability=1.0,
    official_api_documented=0.95,
    metadata_traceability=0.90,
    domain_tier=_GOV,
)

# DataJud (CNJ) — national judicial registry, .jus.br, documented public API
_DATAJUD_PROFILE = SourceVeracityProfile(
    government_domain=1.0,
    legal_authority=1.0,
    public_availability=1.0,
    official_api_documented=0.90,
    metadata_traceability=0.85,
    domain_tier=_GOV,
)

# IBGE — official statistics institute, .gov.br, enrichment-only reference data
_IBGE_PROFILE = SourceVeracityProfile(
    government_domain=1.0,
    legal_authority=0.80,
    public_availability=1.0,
    official_api_documented=1.0,
    metadata_traceability=0.85,
    domain_tier=_GOV,
)

# TCE-RJ — state audit court, exception domain (dados.tcerj.tc.br)
_TCE_RJ_PROFILE = SourceVeracityProfile(
    government_domain=0.80,
    legal_authority=1.0,
    public_availability=1.0,
    official_api_documented=0.90,
    metadata_traceability=0.85,
    domain_tier=_EXC,
)

# TCE-RS — state audit court, .gov.br, strong legal authority
_TCE_RS_PROFILE = SourceVeracityProfile(
    government_domain=1.0,
    legal_authority=0.95,
    public_availability=1.0,
    official_api_documented=0.90,
    metadata_traceability=0.90,
    domain_tier=_GOV,
)

# TCE-SP — state audit court, .gov.br, strong legal authority
_TCE_SP_PROFILE = SourceVeracityProfile(
    government_domain=1.0,
    legal_authority=1.0,
    public_availability=1.0,
    official_api_documented=0.85,
    metadata_traceability=0.85,
    domain_tier=_GOV,
)

# TCE-PE — state audit court, .gov.br, strong legal authority
_TCE_PE_PROFILE = SourceVeracityProfile(
    government_domain=1.0,
    legal_authority=0.95,
    public_availability=1.0,
    official_api_documented=0.85,
    metadata_traceability=0.85,
    domain_tier=_GOV,
)

# Jurisprudência — STF/STJ higher courts, .jus.br
_JURIS_PROFILE = SourceVeracityProfile(
    government_domain=1.0,
    legal_authority=1.0,
    public_availability=1.0,
    official_api_documented=0.80,
    metadata_traceability=0.85,
    domain_tier=_GOV,
)

# Bacen — Banco Central, .gov.br, enrichment-only economic reference
_BACEN_PROFILE = SourceVeracityProfile(
    government_domain=1.0,
    legal_authority=0.90,
    public_availability=1.0,
    official_api_documented=1.0,
    metadata_traceability=0.90,
    domain_tier=_GOV,
)

# BNDES — development bank, .gov.br, financing operations
_BNDES_PROFILE = SourceVeracityProfile(
    government_domain=1.0,
    legal_authority=0.90,
    public_availability=1.0,
    official_api_documented=0.90,
    metadata_traceability=0.85,
    domain_tier=_GOV,
)

# ANVISA/BPS — official health surveillance and procurement references (.gov.br)
_ANVISA_BPS_PROFILE = SourceVeracityProfile(
    government_domain=1.0,
    legal_authority=0.90,
    public_availability=0.95,
    official_api_documented=0.85,
    metadata_traceability=0.80,
    domain_tier=_GOV,
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
    "tse:tse_doacoes": _TSE_PROFILE,
    "tse:tse_despesas_candidatos": _TSE_PROFILE,
    # Receita Federal (3 jobs)
    "receita_cnpj:rf_empresas": _RECEITA_PROFILE,
    "receita_cnpj:rf_socios": _RECEITA_PROFILE,
    "receita_cnpj:rf_estabelecimentos": _RECEITA_PROFILE,
    # Orçamento BIM (1 job)
    "orcamento_bim:orcamento_bim_items": _ORCAMENTO_BIM_PROFILE,
    # Querido Diário (1 job)
    "querido_diario:qd_gazettes": _QD_PROFILE,
    # BrasilAPI CNPJ (1 job)
    "brasilapi_cnpj:brasilapi_cnpj_lookup": _BRASILAPI_CNPJ_PROFILE,
    # TCU — Tribunal de Contas da União (3 jobs)
    "tcu:tcu_inidoneos": _TCU_PROFILE,
    "tcu:tcu_inabilitados": _TCU_PROFILE,
    "tcu:tcu_acordaos": _TCU_PROFILE,
    # DataJud/CNJ — national judicial registry (2 jobs)
    "datajud:datajud_processos_improbidade": _DATAJUD_PROFILE,
    "datajud:datajud_processos_licitacao": _DATAJUD_PROFILE,
    # IBGE — geographic and statistical reference data (2 jobs)
    "ibge:ibge_municipios": _IBGE_PROFILE,
    "ibge:ibge_cnae": _IBGE_PROFILE,
    # TCE-RJ — state audit court, .tc.br (exception domain, strong legal authority)
    "tce_rj:tce_rj_licitacoes": _TCE_RJ_PROFILE,
    "tce_rj:tce_rj_contratos": _TCE_RJ_PROFILE,
    "tce_rj:tce_rj_penalidades": _TCE_RJ_PROFILE,
    # TCE-RS — state audit court, .gov.br
    "tce_rs:tce_rs_gestao_fiscal": _TCE_RS_PROFILE,
    "tce_rs:tce_rs_educacao": _TCE_RS_PROFILE,
    "tce_rs:tce_rs_saude": _TCE_RS_PROFILE,
    # TCE-SP — state audit court, .gov.br
    "tce_sp:tce_sp_despesas": _TCE_SP_PROFILE,
    "tce_sp:tce_sp_receitas": _TCE_SP_PROFILE,
    # TCE-PE — state audit court, .gov.br
    "tce_pe:tce_pe_licitacoes": _TCE_PE_PROFILE,
    "tce_pe:tce_pe_contratos": _TCE_PE_PROFILE,
    "tce_pe:tce_pe_despesas": _TCE_PE_PROFILE,
    # Jurisprudência — STF higher court rulings, .jus.br
    "jurisprudencia:juris_stf_licitacao": _JURIS_PROFILE,
    "jurisprudencia:juris_stf_improbidade": _JURIS_PROFILE,
    # Bacen — Banco Central economic indicators, .gov.br (enrichment-only)
    "bacen:bacen_selic": _BACEN_PROFILE,
    "bacen:bacen_ipca": _BACEN_PROFILE,
    "bacen:bacen_cambio": _BACEN_PROFILE,
    # BNDES — development bank financing operations, .gov.br
    "bndes:bndes_operacoes_auto": _BNDES_PROFILE,
    "bndes:bndes_operacoes_nao_auto": _BNDES_PROFILE,
    # ANVISA/BPS — health procurement prices and drug registry, .gov.br
    "anvisa_bps:anvisa_bps_prices": _ANVISA_BPS_PROFILE,
    "anvisa_bps:anvisa_bulario_registry": _ANVISA_BPS_PROFILE,
}
