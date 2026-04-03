"""Composite signal confidence scorer.

Combines four independent signals into a 0–100 integer score:
  - ER confidence   (40%) — how certain the entity resolution is
  - Data freshness  (25%) — log-decay penalty for stale events
  - Source coverage (20%) — fraction of expected sources present
  - Typology evidence (15%) — typology-specific evidence quality score
"""
from __future__ import annotations

import math
from typing import Optional


def compute_signal_confidence(
    er_confidence: Optional[int],
    days_since_latest_event: int,
    source_coverage: float,
    typology_evidence: float,
) -> tuple[int, dict]:
    """Return (score: int 0–100, factors: dict) for a risk signal.

    Args:
        er_confidence: Cluster confidence from ER (0–100), or None if unmerged (treated as 100).
        days_since_latest_event: Days between signal period_end and today.
        source_coverage: Fraction of expected data sources present (0.0–1.0).
        typology_evidence: Typology-specific evidence quality (0–100).
    """
    er = er_confidence if er_confidence is not None else 100

    freshness = max(0.0, 100 - 20 * math.log(1 + days_since_latest_event))
    coverage = source_coverage * 100
    evidence = typology_evidence

    score = (
        er * 0.40
        + freshness * 0.25
        + coverage * 0.20
        + evidence * 0.15
    )
    return round(score), {
        "er": er,
        "freshness": round(freshness, 1),
        "coverage": round(coverage, 1),
        "evidence": round(evidence, 1),
    }
