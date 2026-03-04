"""ER quality regression test suite.

100-pair dataset: 50 known matches + 50 known non-matches.
Asserts precision >= 0.95 and recall >= 0.90.
"""
import uuid

import pytest

from shared.er.matching import _get_cnpj_raiz, deterministic_match, probabilistic_match
from shared.config import settings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _org(name: str, cnpj: str = "", entity_type: str = "org", **attrs) -> dict:
    identifiers: dict = {}
    if cnpj:
        identifiers["cnpj"] = cnpj
    return {
        "id": uuid.uuid4(),
        "name": name,
        "entity_type": entity_type,
        "identifiers": identifiers,
        "attrs": attrs,
    }


def _person(name: str, cpf_hash: str = "", **attrs) -> dict:
    identifiers: dict = {}
    if cpf_hash:
        identifiers["cpf_hash"] = cpf_hash
    return {
        "id": uuid.uuid4(),
        "name": name,
        "entity_type": "person",
        "identifiers": identifiers,
        "attrs": attrs,
    }


def _is_match(a: dict, b: dict) -> bool:
    """Return True if deterministic OR probabilistic match fires."""
    if deterministic_match(a, b):
        return True
    threshold = (
        settings.PERSON_MATCH_THRESHOLD
        if "person" in (a.get("entity_type"), b.get("entity_type"))
        else settings.ORG_MATCH_THRESHOLD
    )
    return probabilistic_match(a, b, threshold=threshold) is not None


# ---------------------------------------------------------------------------
# CNPJ constants (fictional, structurally valid-looking)
# ---------------------------------------------------------------------------
CNPJ = {
    "alpha":   "11222333000181",
    "beta":    "22333444000192",
    "gamma":   "33444555000103",
    "delta":   "44555666000114",
    "epsilon": "55666777000125",
    "zeta":    "66777888000136",
    "eta":     "77888999000147",
    "theta":   "88999000000158",
    "iota":    "99000111000169",
    "kappa":   "10111222000170",
    # Pairs with same raiz but different suffixes (same company, different branch)
    "alpha2":  "11222333000271",
    "beta2":   "22333444000283",
}

CPF = {
    "joao":    "hash_joao_silva_001",
    "maria":   "hash_maria_santos_002",
    "pedro":   "hash_pedro_costa_003",
    "ana":     "hash_ana_oliveira_004",
    "carlos":  "hash_carlos_souza_005",
}

# ---------------------------------------------------------------------------
# 50 KNOWN MATCH PAIRS
# ---------------------------------------------------------------------------

MATCH_PAIRS = [
    # --- Case / formatting differences (orgs) ---
    (_org("Empresa ABC Ltda", CNPJ["alpha"]),
     _org("EMPRESA ABC LTDA", CNPJ["alpha"])),

    (_org("Construtora Santos S.A.", CNPJ["beta"]),
     _org("Construtora Santos SA", CNPJ["beta"])),

    (_org("Tecnologia Brasil ME", CNPJ["gamma"]),
     _org("TECNOLOGIA BRASIL ME", CNPJ["gamma"])),

    (_org("Serviços Norte S/A", CNPJ["delta"]),
     _org("Servicos Norte SA", CNPJ["delta"])),

    (_org("Comercio Sul Eireli", CNPJ["epsilon"]),
     _org("COMERCIO SUL EIRELI", CNPJ["epsilon"])),

    # --- Abbreviated suffixes ---
    (_org("Distribuidora Leste EPP", CNPJ["zeta"]),
     _org("Distribuidora Leste", CNPJ["zeta"])),

    (_org("Transportes Oeste S.A.", CNPJ["eta"]),
     _org("Transportes Oeste S/A", CNPJ["eta"])),

    (_org("Industria Central LTDA", CNPJ["theta"]),
     _org("Industria Central Ltda.", CNPJ["theta"])),

    # --- Same CNPJ, slight name typo in non-critical part ---
    (_org("Exportadora Rio Verde Ltda", CNPJ["iota"]),
     _org("Exportadora Rio-Verde Ltda", CNPJ["iota"])),

    (_org("Agropecuaria Boa Esperanca ME", CNPJ["kappa"]),
     _org("Agropecuária Boa Esperança ME", CNPJ["kappa"])),

    # --- Same CNPJ identical name (10 deterministic pairs) ---
    (_org("Alpha Corp", CNPJ["alpha"]),   _org("Alpha Corp", CNPJ["alpha"])),
    (_org("Beta Corp", CNPJ["beta"]),     _org("Beta Corp", CNPJ["beta"])),
    (_org("Gamma Corp", CNPJ["gamma"]),   _org("Gamma Corp", CNPJ["gamma"])),
    (_org("Delta Corp", CNPJ["delta"]),   _org("Delta Corp", CNPJ["delta"])),
    (_org("Epsilon Corp", CNPJ["epsilon"]),_org("Epsilon Corp", CNPJ["epsilon"])),
    (_org("Zeta Corp", CNPJ["zeta"]),     _org("Zeta Corp", CNPJ["zeta"])),
    (_org("Eta Corp", CNPJ["eta"]),       _org("Eta Corp", CNPJ["eta"])),
    (_org("Theta Corp", CNPJ["theta"]),   _org("Theta Corp", CNPJ["theta"])),
    (_org("Iota Corp", CNPJ["iota"]),     _org("Iota Corp", CNPJ["iota"])),
    (_org("Kappa Corp", CNPJ["kappa"]),   _org("Kappa Corp", CNPJ["kappa"])),

    # --- Person: same name with/without accents ---
    (_person("João Silva", CPF["joao"]),    _person("Joao Silva", CPF["joao"])),
    (_person("Maria Santos", CPF["maria"]), _person("MARIA SANTOS", CPF["maria"])),
    (_person("Pedro Costa", CPF["pedro"]),  _person("PEDRO COSTA", CPF["pedro"])),
    (_person("Ana Oliveira", CPF["ana"]),   _person("Ana Oliveira", CPF["ana"])),
    (_person("Carlos Souza", CPF["carlos"]),_person("Carlos de Souza", CPF["carlos"])),

    # --- Person: deterministic CPF match with different names ---
    (_person("J. Silva", CPF["joao"]),     _person("João Silva Junior", CPF["joao"])),
    (_person("M. Santos", CPF["maria"]),   _person("Maria dos Santos", CPF["maria"])),
    (_person("P. Costa", CPF["pedro"]),    _person("Pedro H. Costa", CPF["pedro"])),
    (_person("Ana C. Oliveira", CPF["ana"]),_person("Ana Clara Oliveira", CPF["ana"])),
    (_person("Carlos S.", CPF["carlos"]),  _person("Carlos Souza Filho", CPF["carlos"])),

    # --- Brazilian company suffix variations ---
    (_org("Mercado Bom Preco Ltda", CNPJ["alpha2"]),
     _org("Mercado Bom Preco LTDA", CNPJ["alpha2"])),

    (_org("Posto Combustiveis Brasil ME", CNPJ["beta2"]),
     _org("Posto Combustiveis Brasil M.E.", CNPJ["beta2"])),

    # --- Same CNPJ, name abbreviated ---
    (_org("Federacao Nacional dos Trabalhadores", CNPJ["zeta"]),
     _org("Fed Nacional dos Trabalhadores", CNPJ["zeta"])),

    (_org("Instituto de Pesquisa e Desenvolvimento", CNPJ["eta"]),
     _org("Instituto de Pesquisa e Desenv.", CNPJ["eta"])),

    # --- Accentuation and punctuation variants ---
    (_org("Saude & Bem-Estar Clinica", CNPJ["theta"]),
     _org("Saude e Bem Estar Clinica", CNPJ["theta"])),

    (_org("Rede Farmacias Popular Ltda", CNPJ["iota"]),
     _org("Rede Farmácias Popular Ltda", CNPJ["iota"])),

    # --- Numeric variations in name (same CNPJ) ---
    (_org("Construtora 2000 Ltda", CNPJ["kappa"]),
     _org("Construtora Dois Mil Ltda", CNPJ["kappa"])),

    # --- More deterministic same-CNPJ pairs to reach 50 ---
    (_org("Sul Logistica SA",   CNPJ["alpha"]),  _org("Sul Logística S.A.", CNPJ["alpha"])),
    (_org("Norte Comercio ME",  CNPJ["beta"]),   _org("Norte Comercio ME",  CNPJ["beta"])),
    (_org("Leste Servicos Ltda",CNPJ["gamma"]),  _org("Leste Servicos Ltda",CNPJ["gamma"])),
    (_org("Oeste Industria EPP",CNPJ["delta"]),  _org("Oeste Industria EPP",CNPJ["delta"])),
    (_org("Centro Tech SA",     CNPJ["epsilon"]),_org("Centro Tech SA",     CNPJ["epsilon"])),

    # --- Person deterministic pairs ---
    (_person("Roberto Almeida",  "hash_roberto_001"), _person("Roberto Almeida",  "hash_roberto_001")),
    (_person("Fernanda Lima",     "hash_fernanda_002"),_person("Fernanda Lima",     "hash_fernanda_002")),
    (_person("Lucas Ferreira",    "hash_lucas_003"),   _person("Lucas Ferreira",    "hash_lucas_003")),
    (_person("Patricia Gomes",    "hash_patricia_004"),_person("Patricia Gomes",    "hash_patricia_004")),
    (_person("Rodrigo Mendes",    "hash_rodrigo_005"), _person("Rodrigo Mendes",    "hash_rodrigo_005")),

    # --- Name-only probabilistic matches (no CNPJ conflict) ---
    (_org("Farmacia Popular do Brasil"),   _org("Farmácia Popular do Brasil")),
    (_org("Clinica Medica Sao Lucas"),     _org("Clinica Medica São Lucas")),
    (_org("Hospital Municipal Central"),   _org("Hospital Municipal Central")),
]

assert len(MATCH_PAIRS) == 50, f"Expected 50 match pairs, got {len(MATCH_PAIRS)}"

# ---------------------------------------------------------------------------
# 50 KNOWN NON-MATCH PAIRS
# ---------------------------------------------------------------------------

NON_MATCH_PAIRS = [
    # --- Similar names but completely different CNPJs (10 pairs — CNPJ blocking) ---
    (_org("Construtora Norte Ltda", CNPJ["alpha"]),
     _org("Construtora Norte Ltda", CNPJ["beta"])),

    (_org("Servicos Brasil SA", CNPJ["gamma"]),
     _org("Servicos Brasil SA", CNPJ["delta"])),

    (_org("Comercio Central ME", CNPJ["epsilon"]),
     _org("Comercio Central ME", CNPJ["zeta"])),

    (_org("Tech Solutions Ltda", CNPJ["eta"]),
     _org("Tech Solutions Ltda", CNPJ["theta"])),

    (_org("Distribuidora Sul EPP", CNPJ["iota"]),
     _org("Distribuidora Sul EPP", CNPJ["kappa"])),

    (_org("Transportes Rapidos SA", CNPJ["alpha"]),
     _org("Transportes Rapidos SA", CNPJ["gamma"])),

    (_org("Industria Forte Ltda", CNPJ["beta"]),
     _org("Industria Forte Ltda", CNPJ["epsilon"])),

    (_org("Agro Produtora ME", CNPJ["delta"]),
     _org("Agro Produtora ME", CNPJ["zeta"])),

    (_org("Escola Particular ABC", CNPJ["eta"]),
     _org("Escola Particular ABC", CNPJ["kappa"])),

    (_org("Clinica Saude Total SA", CNPJ["iota"]),
     _org("Clinica Saude Total SA", CNPJ["alpha"])),

    # --- Common word overlap but different companies ---
    (_org("Servicos Brasil ME",    CNPJ["alpha"]),
     _org("Comercio Brasil Ltda",  CNPJ["beta"])),

    (_org("Tecnologia Norte SA",   CNPJ["gamma"]),
     _org("Logistica Norte ME",    CNPJ["delta"])),

    (_org("Construtora Rio Ltda",  CNPJ["epsilon"]),
     _org("Distribuidora Rio SA",  CNPJ["zeta"])),

    (_org("Farmacias Sul Eireli",  CNPJ["eta"]),
     _org("Drogarias Sul EPP",     CNPJ["theta"])),

    (_org("Escola Federal Leste",  CNPJ["iota"]),
     _org("Colegio Federal Leste", CNPJ["kappa"])),

    # --- Same common last name, different person (different CPF hash) ---
    (_person("João Silva", "hash_joao_a"),   _person("José Silva",   "hash_jose_b")),
    (_person("Maria Santos", "hash_maria_a"),_person("Ana Santos",   "hash_ana_b")),
    (_person("Pedro Costa", "hash_pedro_a"), _person("Paulo Costa",  "hash_paulo_b")),
    (_person("Carlos Souza", "hash_carlos_a"),_person("Roberto Souza","hash_roberto_c")),
    (_person("Fernanda Lima", "hash_fern_a"),_person("Luciana Lima",  "hash_luci_b")),

    # --- Completely different companies same sector, partial name overlap ---
    (_org("Grupo Carrefour Brasil",   CNPJ["alpha"]),
     _org("Grupo Sendas Brasil",      CNPJ["beta"])),

    (_org("Banco do Brasil SA",       CNPJ["gamma"]),
     _org("Caixa Economica Federal",  CNPJ["delta"])),

    (_org("Petrobras Distribuidora",  CNPJ["epsilon"]),
     _org("Ipiranga Distribuidora",   CNPJ["zeta"])),

    (_org("Embraer Industria Aero",   CNPJ["eta"]),
     _org("Helibras Industria Aero",  CNPJ["theta"])),

    (_org("Sabesp Saneamento",        CNPJ["iota"]),
     _org("Copasa Saneamento",        CNPJ["kappa"])),

    # --- Very different names, no overlap ---
    (_org("Mineradora Amazonia SA",   CNPJ["alpha"]),
     _org("Laticinio Gaucho Ltda",    CNPJ["beta"])),

    (_org("Seguradora Nacional ME",   CNPJ["gamma"]),
     _org("Pesqueira Nordeste SA",    CNPJ["delta"])),

    (_org("Editora Cultura Ltda",     CNPJ["epsilon"]),
     _org("Frigorifico Central ME",   CNPJ["zeta"])),

    (_org("Consultoria Fiscal SA",    CNPJ["eta"]),
     _org("Ceramica Arte Eireli",     CNPJ["theta"])),

    (_org("Viacao Expresso Norte",    CNPJ["iota"]),
     _org("Hotel Fazenda Bela Vista", CNPJ["kappa"])),

    # --- Names similar but CNPJs differ (additional CNPJ blocking tests) ---
    (_org("Construcoes e Reformas Ltda", CNPJ["alpha2"]),
     _org("Construcoes e Reformas Ltda", CNPJ["beta2"])),

    (_org("Rio Verde Agropecuaria SA",  CNPJ["alpha"]),
     _org("Rio Verde Agropecuaria SA",  CNPJ["kappa"])),

    (_org("Max Solucoes Digitais ME",   CNPJ["beta"]),
     _org("Max Solucoes Digitais ME",   CNPJ["eta"])),

    (_org("Grupo Prisma Comercial Ltda",CNPJ["gamma"]),
     _org("Grupo Prisma Comercial Ltda",CNPJ["theta"])),

    (_org("Brasil Import Export SA",    CNPJ["delta"]),
     _org("Brasil Import Export SA",    CNPJ["iota"])),

    # --- Persons with same name but different CPF hash ---
    (_person("Lucas Ferreira",  "hash_lucas_x"), _person("Lucas Ferreira",  "hash_lucas_y")),
    (_person("Juliana Rocha",   "hash_juli_x"),  _person("Juliana Rocha",   "hash_juli_y")),
    (_person("Bruno Martins",   "hash_bruno_x"), _person("Bruno Martins",   "hash_bruno_y")),
    (_person("Camila Torres",   "hash_cam_x"),   _person("Camila Torres",   "hash_cam_y")),
    (_person("Diego Barbosa",   "hash_diego_x"), _person("Diego Barbosa",   "hash_diego_y")),

    # --- Orgs that look similar but are clearly different entities ---
    (_org("Posto Gasolina Boa Vista", CNPJ["alpha"]),
     _org("Boa Vista Supermercados",  CNPJ["beta"])),

    (_org("Oficina Auto Center SA",   CNPJ["gamma"]),
     _org("Auto Pecas Center Ltda",   CNPJ["delta"])),

    (_org("Plano Saude Vida SA",      CNPJ["epsilon"]),
     _org("Plano Odontologico Vida",  CNPJ["zeta"])),

    (_org("Escola de Idiomas Berlitz",CNPJ["eta"]),
     _org("Curso Tecnico Berlim",     CNPJ["theta"])),

    (_org("Fundacao Cultural SP",     CNPJ["iota"]),
     _org("Instituto Cultural RJ",    CNPJ["kappa"])),

    (_org("Cooperativa Agricola Sul", CNPJ["alpha2"]),
     _org("Cooperativa Credito Sul",  CNPJ["beta2"])),

    (_org("Vigilancia Eletronica Pro",CNPJ["alpha"]),
     _org("Vigilancia Patrimonial SA",CNPJ["gamma"])),

    (_org("Sorveteria Neve Fina ME",  CNPJ["beta"]),
     _org("Padaria Pao Quente Ltda",  CNPJ["delta"])),

    (_org("Colégio São Francisco",    CNPJ["epsilon"]),
     _org("Colégio Santo Antonio",    CNPJ["zeta"])),

    (_org("Construtora Omega Ltda",   CNPJ["alpha"]),
     _org("Construtora Sigma SA",     CNPJ["kappa"])),
]

assert len(NON_MATCH_PAIRS) == 50, f"Expected 50 non-match pairs, got {len(NON_MATCH_PAIRS)}"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_er_precision_recall():
    """Precision >= 0.95, recall >= 0.90 over the 100-pair dataset."""
    true_positives = 0
    false_negatives = 0
    false_positives = 0

    for a, b in MATCH_PAIRS:
        if _is_match(a, b):
            true_positives += 1
        else:
            false_negatives += 1

    for a, b in NON_MATCH_PAIRS:
        if _is_match(a, b):
            false_positives += 1

    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 1.0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 1.0

    assert precision >= 0.95, (
        f"Precision {precision:.2f} < 0.95 "
        f"(TP={true_positives}, FP={false_positives})"
    )
    assert recall >= 0.90, (
        f"Recall {recall:.2f} < 0.90 "
        f"(TP={true_positives}, FN={false_negatives})"
    )


def test_cnpj_prefix_blocking():
    """Entities with different CNPJ raiz should be blocked (not compared as match)."""
    # _get_cnpj_raiz extracts first 8 digits
    assert _get_cnpj_raiz("12.345.678/0001-90") == "12345678"
    assert _get_cnpj_raiz("12345678000190") == "12345678"
    assert _get_cnpj_raiz("") == ""
    assert _get_cnpj_raiz("1234567") == ""  # fewer than 8 digits → empty
    assert _get_cnpj_raiz("00000000000000") == "00000000"

    # Two companies with same name but different CNPJ raiz should NOT match
    a = _org("Empresa Identica Ltda", "11222333000181")
    b = _org("Empresa Identica Ltda", "99888777000199")
    assert probabilistic_match(a, b) is None, (
        "CNPJ-prefix blocking must prevent match when raiz differs"
    )

    # Same CNPJ raiz (same first 8 digits, different branch) SHOULD be allowed through
    c = _org("Empresa Identica Ltda", "11222333000181")
    d = _org("Empresa Identica Ltda", "11222333000271")
    # Both have raiz "11222333" — should match (identical names)
    assert probabilistic_match(c, d) is not None, (
        "Same CNPJ raiz should not be blocked"
    )

    # One entity has no CNPJ — should not be blocked
    e = _org("Empresa Identica Ltda")
    f = _org("Empresa Identica Ltda", "99888777000199")
    assert probabilistic_match(e, f) is not None, (
        "Missing CNPJ on one side should not block comparison"
    )


def test_configurable_thresholds():
    """ORG_MATCH_THRESHOLD=0.85, PERSON_MATCH_THRESHOLD=0.90 by default."""
    assert settings.ORG_MATCH_THRESHOLD == 0.85
    assert settings.PERSON_MATCH_THRESHOLD == 0.90
