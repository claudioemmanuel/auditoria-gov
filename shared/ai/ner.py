"""Named Entity Recognition pipeline for Brazilian legal/government texts.

Uses transformers with BERTimbau (neuralmind/bert-base-portuguese-cased)
or falls back to regex-based extraction when transformers is unavailable.
"""

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ExtractedEntity:
    """An entity extracted from text via NER."""

    text: str
    label: str  # PERSON, ORG, MONEY, LAW, DATE, LOC
    start: int
    end: int
    confidence: float = 0.0


# Regex patterns for Brazilian legal/government text
_CNPJ_PATTERN = re.compile(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b")
_CPF_PATTERN = re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b")
_MONEY_PATTERN = re.compile(
    r"R\$\s*[\d.,]+(?:\s*(?:mil|milhões?|bilhões?))?",
    re.IGNORECASE,
)
_LAW_PATTERN = re.compile(
    r"(?:Lei|Decreto|Portaria|Resolução|IN|Instrução Normativa)\s*"
    r"(?:nº\s*)?[\d.]+(?:/\d{4})?",
    re.IGNORECASE,
)
_DATE_PATTERN = re.compile(r"\b\d{1,2}/\d{1,2}/\d{4}\b")

# Cached pipeline
_ner_pipeline = None


def _get_ner_pipeline():
    """Lazy-load the transformers NER pipeline."""
    global _ner_pipeline
    if _ner_pipeline is not None:
        return _ner_pipeline

    try:
        from transformers import pipeline

        _ner_pipeline = pipeline(
            "ner",
            model="neuralmind/bert-base-portuguese-cased",
            aggregation_strategy="simple",
        )
        return _ner_pipeline
    except (ImportError, OSError):
        return None


def _extract_with_regex(text: str) -> list[ExtractedEntity]:
    """Fallback regex-based entity extraction."""
    entities: list[ExtractedEntity] = []

    for match in _CNPJ_PATTERN.finditer(text):
        entities.append(
            ExtractedEntity(
                text=match.group(),
                label="CNPJ",
                start=match.start(),
                end=match.end(),
                confidence=1.0,
            )
        )

    for match in _CPF_PATTERN.finditer(text):
        entities.append(
            ExtractedEntity(
                text=match.group(),
                label="CPF",
                start=match.start(),
                end=match.end(),
                confidence=1.0,
            )
        )

    for match in _MONEY_PATTERN.finditer(text):
        entities.append(
            ExtractedEntity(
                text=match.group(),
                label="MONEY",
                start=match.start(),
                end=match.end(),
                confidence=0.9,
            )
        )

    for match in _LAW_PATTERN.finditer(text):
        entities.append(
            ExtractedEntity(
                text=match.group(),
                label="LAW",
                start=match.start(),
                end=match.end(),
                confidence=0.85,
            )
        )

    for match in _DATE_PATTERN.finditer(text):
        entities.append(
            ExtractedEntity(
                text=match.group(),
                label="DATE",
                start=match.start(),
                end=match.end(),
                confidence=0.9,
            )
        )

    return entities


async def extract_entities_from_text(text: str) -> list[ExtractedEntity]:
    """Extract named entities from Portuguese text.

    Uses BERTimbau NER when available, falls back to regex patterns.
    Returns: person names, org names, monetary values, law references.
    """
    entities: list[ExtractedEntity] = []

    # Always run regex extraction (high precision for structured patterns)
    entities.extend(_extract_with_regex(text))

    # Try transformers-based NER
    pipeline = _get_ner_pipeline()
    if pipeline is not None:
        # Truncate text for model input (512 tokens max)
        truncated = text[:2000]
        try:
            results = pipeline(truncated)
            for r in results:
                label_map = {
                    "PER": "PERSON",
                    "PERSON": "PERSON",
                    "ORG": "ORG",
                    "LOC": "LOC",
                    "MISC": "MISC",
                }
                label = label_map.get(r.get("entity_group", ""), r.get("entity_group", "MISC"))
                entities.append(
                    ExtractedEntity(
                        text=r["word"],
                        label=label,
                        start=r.get("start", 0),
                        end=r.get("end", 0),
                        confidence=float(r.get("score", 0.5)),
                    )
                )
        except Exception:
            pass  # Fallback to regex only

    # Deduplicate by (text, label)
    seen: set[tuple[str, str]] = set()
    unique: list[ExtractedEntity] = []
    for e in entities:
        key = (e.text.strip(), e.label)
        if key not in seen:
            seen.add(key)
            unique.append(e)

    return unique
