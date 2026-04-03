"""Tests for TCE-RS connector — gestão fiscal, educação, saúde."""

import pytest

from openwatch_connectors.base import JobSpec, RateLimitPolicy
from openwatch_connectors.tce_rs import TCERSConnector
from openwatch_models.raw import RawItem


# ── Connector structure ───────────────────────────────────────────────────────


class TestTCERSConnector:
    def setup_method(self):
        self.c = TCERSConnector()

    def test_name(self):
        assert self.c.name == "tce_rs"

    def test_has_3_jobs(self):
        assert len(self.c.list_jobs()) == 3

    def test_job_names(self):
        names = {j.name for j in self.c.list_jobs()}
        assert names == {"tce_rs_gestao_fiscal", "tce_rs_educacao", "tce_rs_saude"}

    def test_all_jobs_enabled(self):
        for job in self.c.list_jobs():
            assert job.enabled is True, f"{job.name} should be enabled"

    def test_rate_limit_policy(self):
        policy = self.c.rate_limit_policy()
        assert isinstance(policy, RateLimitPolicy)
        assert policy.requests_per_second == 2
        assert policy.burst == 4


# ── Normalize ─────────────────────────────────────────────────────────────────


class TestTCERSNormalize:
    def setup_method(self):
        self.c = TCERSConnector()

    def test_normalize_gestao_fiscal(self):
        """Gestão fiscal → org entity + fiscal_compliance/lrf event."""
        items = [RawItem(raw_id="tce_rs_gestao_fiscal:2024:0", data={
            "ano": "2024",
            "codigo_orgao": "8801",
            "nome_orgao": "Porto Alegre",
            "receita_corrente_liquida": 5000000000.0,
            "despesa_pessoal": 2500000000.0,
            "divida_consolidada": 1000000000.0,
            "operacoes_credito": 200000000.0,
            "receita_mde": 1250000000.0,
            "despesa_mde": 1300000000.0,
            "receita_asps": 750000000.0,
            "despesa_asps": 800000000.0,
        })]
        job = JobSpec(name="tce_rs_gestao_fiscal", description="", domain="gestao_fiscal")
        result = self.c.normalize(job, items)

        assert len(result.entities) == 1
        org = result.entities[0]
        assert org.type == "org"
        assert org.identifiers["tce_rs_codigo"] == "8801"
        assert org.name == "Porto Alegre"

        assert len(result.events) == 1
        event = result.events[0]
        assert event.type == "fiscal_compliance"
        assert event.subtype == "lrf"
        assert event.source_connector == "tce_rs"
        assert event.value_brl == 2500000000.0
        assert event.attrs["ano"] == "2024"
        assert event.attrs["receita_corrente_liquida"] == 5000000000.0
        assert event.attrs["despesa_pessoal"] == 2500000000.0
        assert len(event.participants) == 1
        assert event.participants[0].role == "responsible_entity"

    def test_normalize_educacao(self):
        """Education → org entity + fiscal_compliance/education_spending event."""
        items = [RawItem(raw_id="tce_rs_educacao:2024:0", data={
            "ano": "2024",
            "codigo_orgao": "8801",
            "nome_orgao": "Porto Alegre",
            "valor_despesa": 1300000000.0,
            "valor_receita": 1250000000.0,
            "indice": 26.5,
        })]
        job = JobSpec(name="tce_rs_educacao", description="", domain="educacao")
        result = self.c.normalize(job, items)

        assert len(result.entities) == 1
        org = result.entities[0]
        assert org.type == "org"
        assert org.identifiers["tce_rs_codigo"] == "8801"
        assert org.name == "Porto Alegre"

        assert len(result.events) == 1
        event = result.events[0]
        assert event.type == "fiscal_compliance"
        assert event.subtype == "education_spending"
        assert event.source_connector == "tce_rs"
        assert event.value_brl == 1300000000.0
        assert event.attrs["indice"] == 26.5
        assert event.attrs["valor_receita"] == 1250000000.0
        assert len(event.participants) == 1
        assert event.participants[0].role == "responsible_entity"

    def test_normalize_saude(self):
        """Health → org entity + fiscal_compliance/health_spending event."""
        items = [RawItem(raw_id="tce_rs_saude:2024:0", data={
            "ano": "2024",
            "codigo_orgao": "8801",
            "nome_orgao": "Porto Alegre",
            "valor_despesa": 800000000.0,
            "valor_receita": 750000000.0,
            "indice": 18.2,
        })]
        job = JobSpec(name="tce_rs_saude", description="", domain="saude")
        result = self.c.normalize(job, items)

        assert len(result.entities) == 1
        org = result.entities[0]
        assert org.type == "org"
        assert org.identifiers["tce_rs_codigo"] == "8801"
        assert org.name == "Porto Alegre"

        assert len(result.events) == 1
        event = result.events[0]
        assert event.type == "fiscal_compliance"
        assert event.subtype == "health_spending"
        assert event.source_connector == "tce_rs"
        assert event.value_brl == 800000000.0
        assert event.attrs["indice"] == 18.2
        assert event.attrs["valor_receita"] == 750000000.0
        assert len(event.participants) == 1
        assert event.participants[0].role == "responsible_entity"

    def test_normalize_empty_items(self):
        job = JobSpec(name="tce_rs_gestao_fiscal", description="", domain="gestao_fiscal")
        result = self.c.normalize(job, [])
        assert result.entities == []
        assert result.events == []

    def test_normalize_unknown_job_raises(self):
        job = JobSpec(name="tce_rs_unknown", description="", domain="test")
        with pytest.raises(ValueError, match="Unknown TCE-RS job"):
            self.c.normalize(job, [])

    def test_normalize_missing_codigo_orgao(self):
        """Records without codigo_orgao should still produce events, no entity."""
        items = [RawItem(raw_id="tce_rs_educacao:2024:0", data={
            "ano": "2024",
            "nome_orgao": "Município Desconhecido",
            "valor_despesa": 100000.0,
            "valor_receita": 90000.0,
            "indice": 25.0,
        })]
        job = JobSpec(name="tce_rs_educacao", description="", domain="educacao")
        result = self.c.normalize(job, items)

        assert len(result.entities) == 0
        assert len(result.events) == 1
        assert result.events[0].participants == []
        assert result.events[0].value_brl == 100000.0
