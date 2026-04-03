"""Canonical vocabulary for OpenWatch event types and participant roles.

This module is the single source of truth for all string values used in
CanonicalEvent.type and CanonicalEventParticipant.role fields. Connectors
and typologies should import from here instead of using raw string literals.

Usage:
    from shared.models.vocabulary import EventType, ParticipantRole, ROLE_ALIASES

    event = CanonicalEvent(type=EventType.CONTRATO, ...)
    participant = CanonicalEventParticipant(role=ParticipantRole.SUPPLIER, ...)
    canonical_role = ROLE_ALIASES.get(raw_role, raw_role)
"""

from enum import Enum


class EventType(str, Enum):
    """Canonical event types produced by connectors and queried by typologies.

    Values match the strings stored in Event.type in the database.
    New connectors must use values from this enum.
    """

    # ── Sanctions & Compliance ────────────────────────────────────────────
    SANCAO = "sancao"                           # CEIS/CNEP sanctions (Portal da Transparência)

    # ── Procurement ───────────────────────────────────────────────────────
    LICITACAO = "licitacao"                     # Procurement notice / bidding (Compras.gov, PNCP)
    CONTRATO = "contrato"                       # Signed government contract (ComprasNet, PNCP)

    # ── Public Expenditure ────────────────────────────────────────────────
    DESPESA_EXECUCAO = "despesa_execucao"       # Budget execution / payment order
    DESPESA_CARTAO = "despesa_cartao"           # Government card spending
    DESPESA_COTA = "despesa_cota"               # Parliamentary quota expense (CEAP/Câmara)
    DESPESA = "despesa"                         # Generic expense (CEAPS/Senado)
    DESPESA_ELEITORAL = "despesa_eleitoral"     # Campaign spending (TSE)
    EMENDA = "emenda"                           # Parliamentary budget amendment

    # ── Transfers & Agreements ────────────────────────────────────────────
    TRANSFERENCIA = "transferencia"             # Federal transfer (Transfere.gov)
    CONVENIO = "convenio"                       # Intergovernmental agreement

    # ── Personnel & Payroll ───────────────────────────────────────────────
    REMUNERACAO = "remuneracao"                 # Civil servant payroll record
    VIAGEM = "viagem"                           # Official travel

    # ── Benefits & Social Programs ────────────────────────────────────────
    BENEFICIO = "beneficio"                     # Social benefit (e.g. Bolsa Família)

    # ── Corporate Structure ───────────────────────────────────────────────
    SOCIEDADE = "sociedade"                     # Company partnership/QSA record (Receita Federal)

    # ── Electoral ─────────────────────────────────────────────────────────
    CANDIDATURA = "candidatura"                 # Electoral candidacy (TSE)
    PATRIMONIO = "patrimonio"                   # Declared assets (TSE)
    DOACAO_ELEITORAL = "doacao_eleitoral"       # Campaign donation received (TSE)

    # ── Official Gazettes ─────────────────────────────────────────────────
    DIARIO_OFICIAL = "diario_oficial"           # Official gazette entry (Querido Diário)

    # ── Legislative ───────────────────────────────────────────────────────
    LEGISLATIVO = "legislativo"                 # Legislative body record (Câmara/Senado)

    # ── Future Phase 1+ connectors ────────────────────────────────────────
    FINANCIAMENTO = "financiamento"             # Financing / credit operation
    DIVIDA_ATIVA = "divida_ativa"               # Active debt / tax enforcement
    PROCESSO_CVM = "processo_cvm"               # CVM (securities regulator) proceeding
    PENALIDADE_BCB = "penalidade_bcb"           # Central Bank penalty
    EMBARGO_AMBIENTAL = "embargo_ambiental"     # Environmental embargo (IBAMA)
    AUTO_INFRACAO = "auto_infracao"             # Infraction notice / administrative fine
    VINCULO_EMPREGATICIO_AGREGADO = "vinculo_empregaticio_agregado"  # Aggregated employment link
    PEP_DESIGNATION = "pep_designation"         # Politically Exposed Person designation


class ParticipantRole(str, Enum):
    """Canonical participant roles used in CanonicalEventParticipant.role.

    Values match the strings stored in EventParticipant.role in the database.
    """

    # ── Procurement roles ─────────────────────────────────────────────────
    BUYER = "buyer"                             # Contracting authority
    PROCURING_ENTITY = "procuring_entity"       # Formal procuring entity (may differ from buyer)
    SUPPLIER = "supplier"                       # Contract supplier / fornecedor
    WINNER = "winner"                           # Auction winner
    BIDDER = "bidder"                           # Bid participant
    SUBCONTRACTOR = "subcontractor"             # Sub-contracted party

    # ── Enforcement & Sanctions ───────────────────────────────────────────
    SANCTIONED = "sanctioned"                   # Sanctioned entity (CEIS/CNEP)

    # ── Personnel ─────────────────────────────────────────────────────────
    SERVANT = "servant"                         # Civil servant (servidor público)
    BENEFICIARY = "beneficiary"                 # Benefit recipient

    # ── Corporate / Ownership ─────────────────────────────────────────────
    COMPANY = "company"                         # Company in a partnership event
    PARTNER = "partner"                         # Partner/shareholder (sócio)
    ORGAO = "orgao"                             # Government body/entity

    # ── Electoral ─────────────────────────────────────────────────────────
    CANDIDATO = "candidato"                     # Electoral candidate
    DOADOR = "doador"                           # Campaign donor
    FORNECEDOR = "fornecedor"                   # Campaign expense supplier
    SENADOR = "senador"                         # Senator
    BENEFICIARIO = "beneficiario"               # Transfer beneficiary

    # ── Future Phase 1+ roles ─────────────────────────────────────────────
    DEBTOR = "debtor"                           # Active debt debtor
    INVESTIGATED = "investigated"               # Entity under investigation
    PENALIZED = "penalized"                     # Entity subject to penalty
    EMBARGOED = "embargoed"                     # Entity subject to embargo
    PEP = "pep"                                 # Politically Exposed Person
    PEP_ASSOCIATE = "pep_associate"             # Associate of a PEP


# ── Legacy / alternate string → canonical role value ─────────────────────────
ROLE_ALIASES: dict[str, str] = {
    # Procurement aliases
    "contractor": ParticipantRole.SUPPLIER,
    "subcontratado": ParticipantRole.SUBCONTRACTOR,
    # Sanctions aliases
    "sancionado": ParticipantRole.SANCTIONED,
    "target": ParticipantRole.INVESTIGATED,
    # Personnel aliases
    "employee": ParticipantRole.SERVANT,
}
