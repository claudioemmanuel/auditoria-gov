"""Tests for Bacen connector — selic, ipca, cambio."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shared.connectors.base import JobSpec, RateLimitPolicy, SourceClassification
from shared.connectors.bacen import BacenConnector
from shared.models.raw import RawItem


# ── Connector structure ───────────────────────────────────────────────────────


class TestBacenConnector:
    def setup_method(self):
        self.c = BacenConnector()

    def test_name(self):
        assert self.c.name == "bacen"

    def test_has_3_jobs(self):
        assert len(self.c.list_jobs()) == 3

    def test_job_names(self):
        names = {j.name for j in self.c.list_jobs()}
        assert names == {"bacen_selic", "bacen_ipca", "bacen_cambio"}

    def test_all_jobs_enabled(self):
        for job in self.c.list_jobs():
            assert job.enabled is True, f"{job.name} should be enabled"

    def test_classification_is_enrichment_only(self):
        assert self.c.classification == SourceClassification.ENRICHMENT_ONLY

    def test_rate_limit_policy(self):
        policy = self.c.rate_limit_policy()
        assert isinstance(policy, RateLimitPolicy)
        assert policy.requests_per_second == 10
        assert policy.burst == 20


# ── Normalize ─────────────────────────────────────────────────────────────────


class TestBacenNormalize:
    def setup_method(self):
        self.c = BacenConnector()

    def test_normalize_selic(self):
        """Selic → events only, type=indicador_economico, subtype=selic."""
        items = [RawItem(raw_id="bacen_selic:01/07/2024", data={
            "_codigo": 432,
            "_subtype": "selic",
            "data": "01/07/2024",
            "valor": "10.50",
        })]
        job = JobSpec(name="bacen_selic", description="", domain="indicador_economico")
        result = self.c.normalize(job, items)

        assert result.entities == []
        assert len(result.events) == 1

        event = result.events[0]
        assert event.type == "indicador_economico"
        assert event.subtype == "selic"
        assert event.source_connector == "bacen"
        assert event.occurred_at is not None
        assert event.occurred_at.year == 2024
        assert event.attrs["codigo_serie"] == 432
        assert event.attrs["valor"] == 10.50

    def test_normalize_ipca(self):
        """IPCA → events only, subtype=ipca."""
        items = [RawItem(raw_id="bacen_ipca:01/06/2024", data={
            "_codigo": 433,
            "_subtype": "ipca",
            "data": "01/06/2024",
            "valor": "0.21",
        })]
        job = JobSpec(name="bacen_ipca", description="", domain="indicador_economico")
        result = self.c.normalize(job, items)

        assert len(result.events) == 1
        event = result.events[0]
        assert event.subtype == "ipca"
        assert event.attrs["valor"] == 0.21

    def test_normalize_cambio(self):
        """Câmbio → events only, subtype=cambio."""
        items = [RawItem(raw_id="bacen_cambio:01/07/2024", data={
            "_codigo": 3698,
            "_subtype": "cambio",
            "data": "01/07/2024",
            "valor": "5.4321",
        })]
        job = JobSpec(name="bacen_cambio", description="", domain="indicador_economico")
        result = self.c.normalize(job, items)

        assert len(result.events) == 1
        event = result.events[0]
        assert event.subtype == "cambio"
        assert event.attrs["codigo_serie"] == 3698
        assert event.attrs["valor"] == pytest.approx(5.4321)

    def test_normalize_empty_items(self):
        job = JobSpec(name="bacen_selic", description="", domain="indicador_economico")
        result = self.c.normalize(job, [])
        assert result.entities == []
        assert result.events == []

    def test_normalize_skips_bad_valor(self):
        """Items with unparseable valor are skipped gracefully."""
        items = [RawItem(raw_id="bacen_selic:bad", data={
            "_codigo": 432,
            "_subtype": "selic",
            "data": "01/07/2024",
            "valor": "not-a-number",
        })]
        job = JobSpec(name="bacen_selic", description="", domain="indicador_economico")
        result = self.c.normalize(job, items)
        # The normalize catches ValueError and skips the item
        assert len(result.events) == 0
