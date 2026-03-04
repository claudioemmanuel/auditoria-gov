import uuid
from dataclasses import dataclass

from rapidfuzz.distance import JaroWinkler

from shared.config import settings
from shared.er.normalize import normalize_entity_for_matching


def _jaro_winkler_similarity(s1: str, s2: str) -> float:
    """Jaro-Winkler string similarity (0.0 to 1.0). Delegates to rapidfuzz."""
    return JaroWinkler.similarity(s1, s2)


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


def _get_cnpj_raiz(cnpj: str) -> str:
    """Extract CNPJ raiz (first 8 digits, digits only) for blocking."""
    digits = "".join(c for c in cnpj if c.isdigit())
    return digits[:8] if len(digits) >= 8 else ""


def probabilistic_match(
    entity_a: dict, entity_b: dict, threshold: float | None = None
) -> MatchResult | None:
    """Fuzzy match using Jaro-Winkler on normalized names.
    Additional signals: shared address, phone, email boost score.

    Uses per-entity-type thresholds from settings:
    - org/company: settings.ORG_MATCH_THRESHOLD (default 0.85)
    - person: settings.PERSON_MATCH_THRESHOLD (default 0.90)

    CNPJ-prefix blocking: if both entities have a CNPJ raiz and they differ,
    the comparison is skipped (returns None immediately).
    """
    norm_a = normalize_entity_for_matching(entity_a["name"], entity_a["identifiers"])
    norm_b = normalize_entity_for_matching(entity_b["name"], entity_b["identifiers"])

    # CNPJ-prefix blocking
    cnpj_a = norm_a.get("cnpj") or ""
    cnpj_b = norm_b.get("cnpj") or ""
    raiz_a = _get_cnpj_raiz(cnpj_a)
    raiz_b = _get_cnpj_raiz(cnpj_b)
    if raiz_a and raiz_b and raiz_a != raiz_b:
        return None

    # Determine threshold from entity type if not provided explicitly
    if threshold is None:
        entity_type_a = entity_a.get("entity_type", "org")
        entity_type_b = entity_b.get("entity_type", "org")
        is_person = "person" in (entity_type_a, entity_type_b)
        threshold = (
            settings.PERSON_MATCH_THRESHOLD if is_person else settings.ORG_MATCH_THRESHOLD
        )

    name_sim = JaroWinkler.similarity(norm_a["name_norm"], norm_b["name_norm"])

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
