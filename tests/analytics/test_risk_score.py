from datetime import datetime, timedelta, timezone

import pytest

from shared.analytics.risk_score import compute_risk_score_from_signals, _recency_weight


class TestRecencyWeight:
    def test_recent_signal_high_weight(self):
        now = datetime.now(timezone.utc)
        weight = _recency_weight(now)
        assert weight > 0.95

    def test_old_signal_low_weight(self):
        old = datetime.now(timezone.utc) - timedelta(days=365)
        weight = _recency_weight(old)
        assert weight < 0.5

    def test_none_date_default(self):
        weight = _recency_weight(None)
        assert weight == 0.5

    def test_very_old_signal(self):
        very_old = datetime.now(timezone.utc) - timedelta(days=365 * 3)
        weight = _recency_weight(very_old)
        assert weight < 0.1


class TestComputeRiskScore:
    def test_empty_signals(self):
        assert compute_risk_score_from_signals([]) == 0.0

    def test_single_critical_signal(self):
        signals = [
            {"severity": "critical", "confidence": 0.95, "created_at": datetime.now(timezone.utc)},
        ]
        score = compute_risk_score_from_signals(signals)
        assert score > 0
        assert score <= 100

    def test_multiple_signals_higher_than_single(self):
        one = [
            {"severity": "high", "confidence": 0.8, "created_at": datetime.now(timezone.utc)},
        ]
        many = [
            {"severity": "high", "confidence": 0.8, "created_at": datetime.now(timezone.utc)},
            {"severity": "critical", "confidence": 0.9, "created_at": datetime.now(timezone.utc)},
            {"severity": "medium", "confidence": 0.7, "created_at": datetime.now(timezone.utc)},
        ]
        assert compute_risk_score_from_signals(many) > compute_risk_score_from_signals(one)

    def test_critical_higher_than_low(self):
        critical = [
            {"severity": "critical", "confidence": 1.0, "created_at": datetime.now(timezone.utc)},
        ]
        low = [
            {"severity": "low", "confidence": 1.0, "created_at": datetime.now(timezone.utc)},
        ]
        assert compute_risk_score_from_signals(critical) > compute_risk_score_from_signals(low)

    def test_score_bounded(self):
        signals = [
            {"severity": "critical", "confidence": 1.0, "created_at": datetime.now(timezone.utc)}
            for _ in range(50)
        ]
        score = compute_risk_score_from_signals(signals)
        assert 0 <= score <= 100

    def test_old_signals_lower_score(self):
        recent = [
            {"severity": "high", "confidence": 0.8, "created_at": datetime.now(timezone.utc)},
        ]
        old = [
            {"severity": "high", "confidence": 0.8, "created_at": datetime.now(timezone.utc) - timedelta(days=365)},
        ]
        assert compute_risk_score_from_signals(recent) > compute_risk_score_from_signals(old)
