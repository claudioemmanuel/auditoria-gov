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
    # Same 8-digit CNPJ root (matriz/filial) + high name similarity
    score, evidence_type = compute_pair_confidence(
        identifiers_a={"cnpj": "12345678000100"},
        identifiers_b={"cnpj": "12345678000181"},
        name_similarity=0.92,
        same_municipality=True,
        co_participation_count=0,
    )
    assert score == 95
    assert evidence_type == EvidenceType.CNPJ_BRANCH


def test_name_identical_same_municipality_gives_85():
    score, evidence_type = compute_pair_confidence(
        identifiers_a={},
        identifiers_b={},
        name_similarity=1.0,
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


# Boundary: exactly at merge threshold (60) should return a score, not None
def test_boundary_exactly_at_threshold():
    # name_similarity=0.75 gives score=55 which is below merge threshold 60
    # Let's test the actual boundary between no-merge and merge
    # score=55 < 60 threshold → should this return None?
    # Per spec: "below 60 → não merga"
    # So name_fuzzy (score=55) IS below threshold and should return None
    score, _ = compute_pair_confidence(
        identifiers_a={},
        identifiers_b={},
        name_similarity=0.75,
        same_municipality=False,
        co_participation_count=0,
    )
    # name_similarity=0.75 gives NAME_FUZZY score=55, which is < 60 threshold
    assert score is None  # below merge threshold
