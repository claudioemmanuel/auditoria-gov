import pytest

from openwatch_services.case_builder import _max_severity, _SEVERITY_ORDER


class TestMaxSeverity:
    def test_critical_wins(self):
        assert _max_severity("low", "critical") == "critical"

    def test_high_over_medium(self):
        assert _max_severity("medium", "high") == "high"

    def test_same_severity(self):
        assert _max_severity("high", "high") == "high"

    def test_single_severity(self):
        assert _max_severity("low") == "low"

    def test_all_severities(self):
        assert _max_severity("low", "medium", "high", "critical") == "critical"


class TestSeverityOrder:
    def test_order_correct(self):
        assert _SEVERITY_ORDER["low"] < _SEVERITY_ORDER["medium"]
        assert _SEVERITY_ORDER["medium"] < _SEVERITY_ORDER["high"]
        assert _SEVERITY_ORDER["high"] < _SEVERITY_ORDER["critical"]

    def test_all_present(self):
        assert "low" in _SEVERITY_ORDER
        assert "medium" in _SEVERITY_ORDER
        assert "high" in _SEVERITY_ORDER
        assert "critical" in _SEVERITY_ORDER
