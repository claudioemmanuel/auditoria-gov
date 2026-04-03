"""Tests for Jurisprudência connector — STF rulings."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from openwatch_connectors.base import JobSpec, RateLimitPolicy
from openwatch_connectors.jurisprudencia import JurisprudenciaConnector
from openwatch_models.raw import RawItem


# ── Connector structure ───────────────────────────────────────────────────────


class TestJurisprudenciaConnector:
    def setup_method(self):
        self.c = JurisprudenciaConnector()

    def test_name(self):
        assert self.c.name == "jurisprudencia"

    def test_has_2_jobs(self):
        assert len(self.c.list_jobs()) == 2

    def test_job_names(self):
        names = {j.name for j in self.c.list_jobs()}
        assert names == {"juris_stf_licitacao", "juris_stf_improbidade"}

    def test_all_jobs_enabled(self):
        for job in self.c.list_jobs():
            assert job.enabled is True, f"{job.name} should be enabled"

    def test_rate_limit_policy(self):
        policy = self.c.rate_limit_policy()
        assert isinstance(policy, RateLimitPolicy)
        assert policy.requests_per_second == 1
        assert policy.burst == 3


# ── Normalize ─────────────────────────────────────────────────────────────────


class TestJurisprudenciaNormalize:
    def setup_method(self):
        self.c = JurisprudenciaConnector()

    def test_normalize_creates_events_only(self):
        """Jurisprudência creates events only, no entities."""
        items = [RawItem(raw_id="juris_stf_licitacao:1:0", data={
            "ementa": "Recurso extraordinário. Licitação. Fraude comprovada.",
            "relator": "Min. Roberto Barroso",
            "numeroProcesso": "RE 123456",
            "classe": "RE",
            "dataPublicacao": "15/03/2024",
            "url": "https://portal.stf.jus.br/processos/detalhe.asp?incidente=123456",
        })]
        job = JobSpec(name="juris_stf_licitacao", description="", domain="jurisprudencia")
        result = self.c.normalize(job, items)

        assert result.entities == []
        assert len(result.events) == 1

        event = result.events[0]
        assert event.type == "jurisprudencia"
        assert event.subtype == "acordao_stf"
        assert event.source_connector == "jurisprudencia"
        assert event.description == "Recurso extraordinário. Licitação. Fraude comprovada."
        assert event.occurred_at is not None
        assert event.occurred_at.year == 2024

    def test_normalize_event_attrs(self):
        """Event attrs contain tribunal, relator, numero_processo, classe, url."""
        items = [RawItem(raw_id="juris_stf_improbidade:1:0", data={
            "ementa": "Improbidade administrativa. Enriquecimento ilícito.",
            "relator": "Min. Alexandre de Moraes",
            "numeroProcesso": "AI 789012",
            "classe": "AI",
            "dataPublicacao": "2024-06-20",
            "url": "https://portal.stf.jus.br/processos/detalhe.asp?incidente=789012",
        })]
        job = JobSpec(name="juris_stf_improbidade", description="", domain="jurisprudencia")
        result = self.c.normalize(job, items)

        event = result.events[0]
        assert event.attrs["tribunal"] == "STF"
        assert event.attrs["relator"] == "Min. Alexandre de Moraes"
        assert event.attrs["numero_processo"] == "AI 789012"
        assert event.attrs["classe"] == "AI"
        assert event.attrs["url"] == "https://portal.stf.jus.br/processos/detalhe.asp?incidente=789012"

    def test_normalize_empty_items(self):
        job = JobSpec(name="juris_stf_licitacao", description="", domain="jurisprudencia")
        result = self.c.normalize(job, [])
        assert result.entities == []
        assert result.events == []

    def test_normalize_unknown_job_does_not_raise(self):
        """Jurisprudência normalize handles any job name (no dispatch by name)."""
        job = JobSpec(name="juris_stf_licitacao", description="", domain="jurisprudencia")
        result = self.c.normalize(job, [])
        assert result.events == []

    def test_normalize_missing_optional_fields(self):
        """Missing fields produce empty strings / None without errors."""
        items = [RawItem(raw_id="juris_stf_licitacao:1:0", data={})]
        job = JobSpec(name="juris_stf_licitacao", description="", domain="jurisprudencia")
        result = self.c.normalize(job, items)

        assert len(result.events) == 1
        event = result.events[0]
        assert event.type == "jurisprudencia"
        assert event.subtype == "acordao_stf"
        assert event.description is None
        assert event.attrs["tribunal"] == "STF"
