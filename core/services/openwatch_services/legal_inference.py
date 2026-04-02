"""Legal inference engine — maps typology signal clusters to legal violation hypotheses.

Rules are deterministic: same signal cluster → same hypotheses.
Confidence scores are fixed per rule (not ML-based).
All results are stored in legal_violation_hypothesis table.
"""

import uuid
from sqlalchemy import select
from sqlalchemy.orm import Session

from openwatch_utils.logging import log
from openwatch_models.orm import LegalViolationHypothesis


# Rule: (frozenset of typology codes that must ALL be present) → list of hypothesis dicts
# Each hypothesis: {law_name, article, violation_type, confidence}
# Rules are checked in ORDER — a case can match multiple rules.
# More specific rules (more codes required) are listed first.

_INFERENCE_RULES: list[tuple[frozenset, list[dict]]] = [
    # High-specificity compound rules (most specific first)
    (
        frozenset({"T02", "T07", "T12"}),
        [{"law_name": "Lei 14.133/2021", "article": "Art. 337-E", "violation_type": "fraude_licitatoria", "confidence": 0.90}],
    ),
    (
        frozenset({"T11", "T03", "T05"}),
        [{"law_name": "Lei 14.133/2021", "article": "Art. 337-K", "violation_type": "fraude_licitatoria", "confidence": 0.88},
         {"law_name": "Código Penal", "article": "Art. 312", "violation_type": "peculato", "confidence": 0.70}],
    ),
    (
        frozenset({"T06", "T17"}),
        [{"law_name": "Lei 9.613/1998", "article": "Art. 1°", "violation_type": "lavagem", "confidence": 0.85},
         {"law_name": "Lei 12.846/2013", "article": "Art. 5°", "violation_type": "corrupcao_ativa", "confidence": 0.75}],
    ),
    (
        frozenset({"T13", "T12"}),
        [{"law_name": "Lei 8.429/1992", "article": "Art. 9°, I", "violation_type": "corrupcao_passiva", "confidence": 0.85},
         {"law_name": "Lei 14.133/2021", "article": "Art. 9°, IV", "violation_type": "fraude_licitatoria", "confidence": 0.80}],
    ),
    (
        frozenset({"T02", "T12"}),
        [{"law_name": "Lei 14.133/2021", "article": "Art. 337-F", "violation_type": "fraude_licitatoria", "confidence": 0.80}],
    ),
    (
        frozenset({"T03", "T11"}),
        [{"law_name": "Lei 14.133/2021", "article": "Art. 337-K", "violation_type": "fraude_licitatoria", "confidence": 0.82}],
    ),
    (
        frozenset({"T02", "T07"}),
        [{"law_name": "Lei 14.133/2021", "article": "Art. 337-F", "violation_type": "fraude_licitatoria", "confidence": 0.75},
         {"law_name": "Lei 12.529/2011", "article": "Art. 36", "violation_type": "corrupcao_ativa", "confidence": 0.70}],
    ),
    # Single-typology strong rules
    (
        frozenset({"T07"}),
        [{"law_name": "Lei 12.529/2011", "article": "Art. 36", "violation_type": "corrupcao_ativa", "confidence": 0.75}],
    ),
    (
        frozenset({"T08"}),
        [{"law_name": "Lei 8.429/1992", "article": "Art. 9°", "violation_type": "corrupcao_passiva", "confidence": 0.92}],
    ),
    (
        frozenset({"T13"}),
        [{"law_name": "Lei 8.429/1992", "article": "Art. 9°, I", "violation_type": "corrupcao_passiva", "confidence": 0.83},
         {"law_name": "Lei 12.813/2013", "article": "Art. 5°", "violation_type": "nepotismo_clientelismo", "confidence": 0.78}],
    ),
    (
        frozenset({"T17"}),
        [{"law_name": "Lei 9.613/1998", "article": "Art. 1°", "violation_type": "lavagem", "confidence": 0.78}],
    ),
    (
        frozenset({"T18"}),
        [{"law_name": "CF/88", "article": "Art. 37, XVI–XVII", "violation_type": "nepotismo_clientelismo", "confidence": 0.88}],
    ),
    (
        frozenset({"T14"}),
        [{"law_name": "Código Penal", "article": "Art. 317", "violation_type": "corrupcao_passiva", "confidence": 0.72}],
    ),
    (
        frozenset({"T22"}),
        [{"law_name": "Lei 8.429/1992", "article": "Art. 9°, I", "violation_type": "nepotismo_clientelismo", "confidence": 0.70}],
    ),
]


def infer_legal_hypotheses_sync(
    case_id: uuid.UUID,
    typology_codes: set[str],
    session: Session,
) -> list[LegalViolationHypothesis]:
    """Infer legal violation hypotheses for a case based on its typology codes.

    Runs all rules in order, matching those where the rule's required codes
    are a SUBSET of the case's typology_codes.

    Uses INSERT ... ON CONFLICT DO UPDATE (upsert) via delete+insert pattern
    with the unique constraint (case_id, law_name, article).

    Returns the list of LegalViolationHypothesis rows created/updated.
    """
    if not typology_codes:
        return []

    code_set = frozenset(typology_codes)
    results: list[LegalViolationHypothesis] = []

    for required_codes, hypotheses in _INFERENCE_RULES:
        if not required_codes.issubset(code_set):
            continue

        matched_codes = sorted(required_codes)

        for hyp in hypotheses:
            # Upsert: update existing matching row or insert fresh
            existing_stmt = select(LegalViolationHypothesis).where(
                LegalViolationHypothesis.case_id == case_id,
                LegalViolationHypothesis.law_name == hyp["law_name"],
                LegalViolationHypothesis.article == hyp.get("article"),
            )
            existing = session.execute(existing_stmt).scalar_one_or_none()

            if existing is not None:
                existing.signal_cluster = matched_codes
                existing.violation_type = hyp.get("violation_type")
                existing.confidence = hyp["confidence"]
                results.append(existing)
            else:
                row = LegalViolationHypothesis(
                    case_id=case_id,
                    signal_cluster=matched_codes,
                    law_name=hyp["law_name"],
                    article=hyp.get("article"),
                    violation_type=hyp.get("violation_type"),
                    confidence=hyp["confidence"],
                )
                session.add(row)
                results.append(row)

    if results:
        session.flush()
        log.info(
            "legal_inference.hypotheses_created",
            case_id=str(case_id),
            n_hypotheses=len(results),
            typology_codes=sorted(typology_codes),
        )

    return results
