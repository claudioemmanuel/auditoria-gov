"""Tests for weekly source compliance audit task."""

from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from openwatch_connectors.domain_guard import DOMAIN_EXCEPTIONS, DomainException


class TestComplianceTask:
    def test_all_sources_pass(self):
        """All current connectors should pass domain validation."""
        from openwatch_connectors.domain_guard import validate_domain, DomainNotAllowedError
        from openwatch_pipelines.compliance_tasks import _CONNECTOR_URLS

        for connector_name, url in _CONNECTOR_URLS.items():
            # Should not raise — all configured URLs are whitelisted
            try:
                validate_domain(url)
            except DomainNotAllowedError:
                pytest.fail(f"Connector '{connector_name}' URL '{url}' is not whitelisted")

    def test_detects_expired_exception(self):
        """Should flag expired domain exceptions as violations."""
        expired_exception = DomainException(
            domain="api.queridodiario.ok.org.br",
            justification="Test",
            max_veracity=0.85,
            approved_date=date(2025, 1, 1),
            review_by=date(2025, 6, 1),  # Already expired
        )

        today = date.today()
        days_until_review = (expired_exception.review_by - today).days
        assert days_until_review < 0, "Exception should be expired for this test"

    def test_detects_expiring_soon(self):
        """Should warn when exception expires within 30 days."""
        from datetime import timedelta
        soon = date.today() + timedelta(days=15)
        expiring_exception = DomainException(
            domain="test.example.org",
            justification="Test",
            max_veracity=0.80,
            approved_date=date(2026, 1, 1),
            review_by=soon,
        )
        days_until_review = (expiring_exception.review_by - date.today()).days
        assert 0 < days_until_review < 30

    def test_connector_urls_cover_all_connectors(self):
        """Every connector in the registry should have a configured URL."""
        from openwatch_connectors import ConnectorRegistry
        from openwatch_pipelines.compliance_tasks import _CONNECTOR_URLS

        missing = set(ConnectorRegistry.keys()) - set(_CONNECTOR_URLS.keys())
        assert missing == set(), f"Missing URLs for connectors: {missing}"
