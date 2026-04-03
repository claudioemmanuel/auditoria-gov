from __future__ import annotations
from enum import Enum
from typing import Optional

MERGE_THRESHOLD = 60


class EvidenceType(str, Enum):
    CNPJ_EXACT = "cnpj_exact"
    CPF_EXACT = "cpf_exact"
    CNPJ_BRANCH = "cnpj_branch"
    NAME_MUNICIPALITY = "name_municipality"
    NAME_CO_PARTICIPATION = "name_co_participation"
    NAME_FUZZY = "name_fuzzy"


def compute_pair_confidence(
    identifiers_a: dict,
    identifiers_b: dict,
    name_similarity: float,
    same_municipality: bool,
    co_participation_count: int,
) -> tuple[Optional[int], Optional[EvidenceType]]:
    """Return (score, evidence_type) for the highest matching tier, or (None, None) if no evidence tier matched.

    Precondition: CNPJ values in identifiers must be digits-only, 14 characters (post-normalization).
    Callers must check score against MERGE_THRESHOLD to decide whether to merge.
    """
    cnpj_a = identifiers_a.get("cnpj")
    cnpj_b = identifiers_b.get("cnpj")
    cpf_a = identifiers_a.get("cpf_hash")
    cpf_b = identifiers_b.get("cpf_hash")

    # Hard matches — always merge
    if cnpj_a and cnpj_b and cnpj_a == cnpj_b:
        return 100, EvidenceType.CNPJ_EXACT
    if cpf_a and cpf_b and cpf_a == cpf_b:
        return 100, EvidenceType.CPF_EXACT

    # CNPJ matriz/filial: same 8-digit root, different branch — structural match only
    if cnpj_a and cnpj_b and cnpj_a[:8] == cnpj_b[:8] and cnpj_a != cnpj_b:
        return 95, EvidenceType.CNPJ_BRANCH

    # Name-based matching
    if name_similarity >= 0.85 and same_municipality:
        return 85, EvidenceType.NAME_MUNICIPALITY

    if name_similarity >= 0.85 and co_participation_count >= 1:
        return 75, EvidenceType.NAME_CO_PARTICIPATION

    if name_similarity >= 0.75:
        return 55, EvidenceType.NAME_FUZZY

    return None, None


def compute_cluster_confidence(pair_scores: list[int]) -> int:
    """Cluster confidence = minimum of all pairwise scores (weakest link)."""
    if not pair_scores:
        return 100
    return min(pair_scores)
