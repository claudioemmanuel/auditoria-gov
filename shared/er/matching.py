import uuid
from dataclasses import dataclass

from shared.er.normalize import normalize_entity_for_matching


@dataclass
class MatchResult:
    entity_a_id: uuid.UUID
    entity_b_id: uuid.UUID
    match_type: str  # "deterministic" or "probabilistic"
    score: float
    reason: str


def deterministic_match(
    entity_a: dict, entity_b: dict
) -> MatchResult | None:
    """Exact-match on CNPJ or CPF hash. Score = 1.0 if matched."""
    norm_a = normalize_entity_for_matching(entity_a["name"], entity_a["identifiers"])
    norm_b = normalize_entity_for_matching(entity_b["name"], entity_b["identifiers"])

    # CNPJ exact match
    if norm_a["cnpj"] and norm_b["cnpj"] and norm_a["cnpj"] == norm_b["cnpj"]:
        return MatchResult(
            entity_a_id=entity_a["id"],
            entity_b_id=entity_b["id"],
            match_type="deterministic",
            score=1.0,
            reason=f"CNPJ match: {norm_a['cnpj']}",
        )

    # CPF hash exact match
    if (
        norm_a["cpf_hash"]
        and norm_b["cpf_hash"]
        and norm_a["cpf_hash"] == norm_b["cpf_hash"]
    ):
        return MatchResult(
            entity_a_id=entity_a["id"],
            entity_b_id=entity_b["id"],
            match_type="deterministic",
            score=1.0,
            reason="CPF hash match",
        )

    return None


def _jaro_winkler_similarity(s1: str, s2: str) -> float:
    """Jaro-Winkler string similarity (0.0 to 1.0)."""
    if s1 == s2:
        return 1.0
    if not s1 or not s2:
        return 0.0

    max_dist = max(len(s1), len(s2)) // 2 - 1
    if max_dist < 0:
        max_dist = 0

    s1_matches = [False] * len(s1)
    s2_matches = [False] * len(s2)

    matches = 0
    transpositions = 0

    for i in range(len(s1)):
        start = max(0, i - max_dist)
        end = min(i + max_dist + 1, len(s2))
        for j in range(start, end):
            if s2_matches[j] or s1[i] != s2[j]:
                continue
            s1_matches[i] = True
            s2_matches[j] = True
            matches += 1
            break

    if matches == 0:
        return 0.0

    k = 0
    for i in range(len(s1)):
        if not s1_matches[i]:
            continue
        while not s2_matches[k]:
            k += 1
        if s1[i] != s2[k]:
            transpositions += 1
        k += 1

    jaro = (
        matches / len(s1) + matches / len(s2) + (matches - transpositions / 2) / matches
    ) / 3

    # Winkler adjustment
    prefix = 0
    for i in range(min(4, len(s1), len(s2))):
        if s1[i] == s2[i]:
            prefix += 1
        else:
            break

    return jaro + prefix * 0.1 * (1 - jaro)


def probabilistic_match(
    entity_a: dict, entity_b: dict, threshold: float = 0.85
) -> MatchResult | None:
    """Fuzzy match using Jaro-Winkler on normalized names.
    Additional signals: shared address, phone, email boost score.
    """
    norm_a = normalize_entity_for_matching(entity_a["name"], entity_a["identifiers"])
    norm_b = normalize_entity_for_matching(entity_b["name"], entity_b["identifiers"])

    name_sim = _jaro_winkler_similarity(norm_a["name_norm"], norm_b["name_norm"])

    # Boost for shared tokens
    if norm_a["tokens"] and norm_b["tokens"]:
        overlap = len(norm_a["tokens"] & norm_b["tokens"])
        total = len(norm_a["tokens"] | norm_b["tokens"])
        token_sim = overlap / total if total > 0 else 0
    else:
        token_sim = 0

    # Boost for shared secondary identifiers
    boost = 0.0
    attrs_a = entity_a.get("attrs", {})
    attrs_b = entity_b.get("attrs", {})
    for field in ("address", "phone", "email"):
        if attrs_a.get(field) and attrs_b.get(field) and attrs_a[field] == attrs_b[field]:
            boost += 0.05

    score = name_sim * 0.6 + token_sim * 0.3 + boost

    if score >= threshold:
        return MatchResult(
            entity_a_id=entity_a["id"],
            entity_b_id=entity_b["id"],
            match_type="probabilistic",
            score=score,
            reason=f"Name similarity: {name_sim:.2f}, token overlap: {token_sim:.2f}",
        )

    return None
