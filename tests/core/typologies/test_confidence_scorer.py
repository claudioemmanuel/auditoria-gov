"""Tests for composite signal confidence scorer (P3.2)."""
import math

import pytest

from openwatch_typologies.confidence_scorer import compute_signal_confidence


def test_full_confidence_all_sources_fresh():
    score, factors = compute_signal_confidence(
        er_confidence=100,
        days_since_latest_event=0,
        source_coverage=1.0,
        typology_evidence=100,
    )
    assert score == 100


def test_data_freshness_decay_at_30_days():
    _, factors = compute_signal_confidence(
        er_confidence=100,
        days_since_latest_event=30,
        source_coverage=1.0,
        typology_evidence=100,
    )
    expected = max(0, 100 - 20 * math.log(1 + 30))
    assert abs(factors["freshness"] - expected) < 1


def test_low_er_confidence_drags_score():
    score, _ = compute_signal_confidence(
        er_confidence=55,
        days_since_latest_event=10,
        source_coverage=0.8,
        typology_evidence=90,
    )
    assert score < 80


def test_er_confidence_none_treated_as_100():
    score_none, _ = compute_signal_confidence(
        er_confidence=None,
        days_since_latest_event=0,
        source_coverage=1.0,
        typology_evidence=100,
    )
    score_100, _ = compute_signal_confidence(
        er_confidence=100,
        days_since_latest_event=0,
        source_coverage=1.0,
        typology_evidence=100,
    )
    assert score_none == score_100


def test_zero_coverage_lowers_score():
    score_full, _ = compute_signal_confidence(
        er_confidence=100, days_since_latest_event=0,
        source_coverage=1.0, typology_evidence=100,
    )
    score_zero, _ = compute_signal_confidence(
        er_confidence=100, days_since_latest_event=0,
        source_coverage=0.0, typology_evidence=100,
    )
    assert score_zero < score_full


def test_freshness_cannot_go_below_zero():
    _, factors = compute_signal_confidence(
        er_confidence=100,
        days_since_latest_event=10_000,
        source_coverage=1.0,
        typology_evidence=100,
    )
    assert factors["freshness"] >= 0


def test_score_is_integer():
    score, _ = compute_signal_confidence(
        er_confidence=75, days_since_latest_event=5,
        source_coverage=0.9, typology_evidence=80,
    )
    assert isinstance(score, int)


def test_factors_keys_present():
    _, factors = compute_signal_confidence(
        er_confidence=80, days_since_latest_event=15,
        source_coverage=0.7, typology_evidence=85,
    )
    assert set(factors.keys()) == {"er", "freshness", "coverage", "evidence"}
