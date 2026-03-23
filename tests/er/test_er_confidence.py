import pytest
from shared.er.confidence import compute_pair_confidence, compute_cluster_confidence, EvidenceType


def test_cnpj_exact_match_gives_100():
    score, evidence_type = compute_pair_confidence(
        identifiers_a={"cnpj": "12345678000100"},
        identifiers_b={"cnpj": "12345678000100"},
        name_similarity=0.95,
        same_municipality=True,
        co_participation_count=0,
    )
    assert score == 100
    assert evidence_type == EvidenceType.CNPJ_EXACT


def test_cpf_exact_match_gives_100():
    score, evidence_type = compute_pair_confidence(
        identifiers_a={"cpf_hash": "abc123"},
        identifiers_b={"cpf_hash": "abc123"},
        name_similarity=0.90,
        same_municipality=False,
        co_participation_count=0,
    )
    assert score == 100
    assert evidence_type == EvidenceType.CPF_EXACT


def test_cnpj_branch_match_gives_95():
    # Same 8-digit CNPJ root (matriz/filial) — structural match, not name-based
    score, evidence_type = compute_pair_confidence(
        identifiers_a={"cnpj": "12345678000100"},
        identifiers_b={"cnpj": "12345678000181"},
        name_similarity=0.50,  # low similarity — must not affect branch detection
        same_municipality=False,
        co_participation_count=0,
    )
    assert score == 95
    assert evidence_type == EvidenceType.CNPJ_BRANCH


def test_cnpj_branch_ignores_name_similarity():
    # Branch identity is a structural fact; name_similarity must not gate it
    score, evidence_type = compute_pair_confidence(
        identifiers_a={"cnpj": "12345678000195"},
        identifiers_b={"cnpj": "12345678000277"},
        name_similarity=0.20,
        same_municipality=False,
        co_participation_count=0,
    )
    assert score == 95
    assert evidence_type == EvidenceType.CNPJ_BRANCH


def test_name_fuzzy_same_municipality_gives_85():
    # NAME_MUNICIPALITY fires for similarity >= 0.85, not just exact matches
    score, evidence_type = compute_pair_confidence(
        identifiers_a={},
        identifiers_b={},
        name_similarity=0.88,
        same_municipality=True,
        co_participation_count=0,
    )
    assert score == 85
    assert evidence_type == EvidenceType.NAME_MUNICIPALITY


def test_name_identical_same_municipality_gives_85():
    score, evidence_type = compute_pair_confidence(
        identifiers_a={},
        identifiers_b={},
        name_similarity=0.90,
        same_municipality=True,
        co_participation_count=0,
    )
    assert score == 85
    assert evidence_type == EvidenceType.NAME_MUNICIPALITY


def test_name_fuzzy_with_co_participation_gives_75():
    score, evidence_type = compute_pair_confidence(
        identifiers_a={},
        identifiers_b={},
        name_similarity=0.87,
        same_municipality=False,
        co_participation_count=3,
    )
    assert score == 75
    assert evidence_type == EvidenceType.NAME_CO_PARTICIPATION


def test_name_fuzzy_only_gives_55():
    score, evidence_type = compute_pair_confidence(
        identifiers_a={},
        identifiers_b={},
        name_similarity=0.78,
        same_municipality=False,
        co_participation_count=0,
    )
    assert score == 55
    assert evidence_type == EvidenceType.NAME_FUZZY


def test_below_threshold_returns_none():
    score, evidence_type = compute_pair_confidence(
        identifiers_a={},
        identifiers_b={},
        name_similarity=0.50,
        same_municipality=False,
        co_participation_count=0,
    )
    assert score is None
    assert evidence_type is None


def test_cluster_confidence_is_min_of_pairs():
    assert compute_cluster_confidence([100, 85, 75]) == 75


def test_cluster_confidence_single_pair():
    assert compute_cluster_confidence([95]) == 95


def test_cluster_confidence_empty_returns_100():
    # No pairs = entity not merged with anything = full confidence
    assert compute_cluster_confidence([]) == 100


def test_name_fuzzy_returns_score_below_merge_threshold():
    # NAME_FUZZY score=55 is returned by compute_pair_confidence.
    # The CALLER is responsible for checking MERGE_THRESHOLD — this function scores, not decides.
    from shared.er.confidence import MERGE_THRESHOLD

    score, evidence_type = compute_pair_confidence(
        identifiers_a={},
        identifiers_b={},
        name_similarity=0.75,
        same_municipality=False,
        co_participation_count=0,
    )
    assert score == 55
    assert evidence_type == EvidenceType.NAME_FUZZY
    # Callers must check: score < MERGE_THRESHOLD → do not merge
    assert score < MERGE_THRESHOLD


def test_below_fuzzy_entry_threshold_returns_none():
    # name_similarity below 0.75 → no evidence tier matched → (None, None)
    score, evidence_type = compute_pair_confidence(
        identifiers_a={},
        identifiers_b={},
        name_similarity=0.60,
        same_municipality=False,
        co_participation_count=0,
    )
    assert score is None
    assert evidence_type is None
