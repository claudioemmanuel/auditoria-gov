import re

from shared.utils.text import normalize_name, strip_accents


def normalize_entity_for_matching(entity_name: str, identifiers: dict) -> dict:
    """Normalize an entity's fields for matching purposes.

    Returns a dict with normalized fields:
    - name_norm: uppercase, no accents, clean whitespace
    - cnpj: digits only (if present)
    - cpf_hash: hash (if present, already hashed at ingest)
    - tokens: set of name tokens for fuzzy matching
    """
    name_norm = normalize_name(entity_name)

    cnpj = identifiers.get("cnpj")
    if cnpj:
        cnpj = re.sub(r"\D", "", cnpj)

    tokens = set(name_norm.split())
    # Remove common stop words for better matching
    stop_words = {"DE", "DA", "DO", "DAS", "DOS", "E", "S", "A", "SA", "LTDA", "ME", "EIRELI"}
    tokens -= stop_words

    return {
        "name_norm": name_norm,
        "cnpj": cnpj,
        "cpf_hash": identifiers.get("cpf_hash"),
        "tokens": tokens,
    }
