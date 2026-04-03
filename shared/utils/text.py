import re
import unicodedata


def strip_accents(text: str) -> str:
    """Remove accents/diacritics from text."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def clean_whitespace(text: str) -> str:
    """Collapse multiple whitespace into single spaces and strip."""
    return re.sub(r"\s+", " ", text).strip()


def normalize_name(name: str) -> str:
    """Normalize a name for matching: uppercase, strip accents, clean whitespace."""
    result = name.upper()
    result = strip_accents(result)
    result = clean_whitespace(result)
    return result
