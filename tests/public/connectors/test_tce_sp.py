"""Tests for TCE-SP connector — despesas, receitas."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from openwatch_connectors.base import JobSpec, RateLimitPolicy
from openwatch_connectors.tce_sp import TCESPConnector, _parse_brl_string
from openwatch_models.raw import RawItem


# ── Connector structure ───────────────────────────────────────────────────────


class TestTCESPConnector:
    def setup_method(self):
        self.c = TCESPConnector()

    def test_name(self):
        assert self.c.name == "tce_sp"

    def test_has_2_jobs(self):
        assert len(self.c.list_jobs()) == 2

    def test_job_names(self):
        names = {j.name for j in self.c.list_jobs()}
        assert names == {"tce_sp_despesas", "tce_sp_receitas"}

    def test_all_jobs_enabled(self):
        for job in self.c.list_jobs():
            assert job.enabled is True, f"{job.name} should be enabled"

    def test_rate_limit_policy(self):
        policy = self.c.rate_limit_policy()
        assert isinstance(policy, RateLimitPolicy)
        assert policy.requests_per_second == 5
        assert policy.burst == 10


# ── BRL string parser ────────────────────────────────────────────────────────


class TestParseBrlString:
    def test_typical_brazilian_format(self):
        assert _parse_brl_string("1.234,56") == 1234.56

    def test_integer_with_dots(self):
        assert _parse_brl_string("1.000.000") == 1000000.0

    def test_plain_number(self):
        assert _parse_brl_string("42") == 42.0

    def test_none_returns_none(self):
        assert _parse_brl_string(None) is None

    def test_empty_string_returns_none(self):
        assert _parse_brl_string("") is None

    def test_dash_returns_none(self):
        assert _parse_brl_string("-") is None

    def test_whitespace_stripped(self):
        assert _parse_brl_string("  1.500,00  ") == 1500.0


# ── Normalize ─────────────────────────────────────────────────────────────────


class TestTCESPNormalize:
    def setup_method(self):
        self.c = TCESPConnector()

    def test_normalize_despesa(self):
        """Despesa → municipality (org) + supplier (company) + expense event."""
        items = [RawItem(raw_id="tce_sp_despesas:m0y2024m3:0", data={
            "municipio": "Campinas",
            "exercicio": "2024",
            "mes": "3",
            "credor": "Empresa de Serviços Ltda",
            "cnpj_credor": "12345678000199",
            "valor_pago": "150.000,50",
            "valor_empenhado": "200.000,00",
            "valor_liquidado": "150.000,50",
            "funcao": "Saúde",
            "subfuncao": "Atenção Básica",
        })]
        job = JobSpec(name="tce_sp_despesas", description="", domain="despesa_municipal")
        result = self.c.normalize(job, items)

        assert len(result.entities) == 2
        muni = result.entities[0]
        assert muni.type == "org"
        assert muni.name == "Campinas"
        assert muni.attrs["uf"] == "SP"

        supplier = result.entities[1]
        assert supplier.type == "company"
        assert supplier.identifiers["cnpj"] == "12345678000199"
        assert supplier.name == "Empresa de Serviços Ltda"

        assert len(result.events) == 1
        event = result.events[0]
        assert event.type == "despesa_municipal"
        assert event.subtype == "despesa"
        assert event.value_brl == 150000.50
        assert event.attrs["municipio"] == "Campinas"
        assert event.attrs["funcao"] == "Saúde"
        assert len(event.participants) == 2
        assert event.participants[0].role == "buyer"
        assert event.participants[1].role == "supplier"

    def test_normalize_despesa_falls_back_to_empenhado(self):
        """When valor_pago is absent, use valor_empenhado."""
        items = [RawItem(raw_id="tce_sp_despesas:m0y2024m1:0", data={
            "municipio": "Santos",
            "exercicio": "2024",
            "mes": "1",
            "credor": "Fornecedor X",
            "cnpj_credor": "98765432000188",
            "valor_empenhado": "50.000,00",
        })]
        job = JobSpec(name="tce_sp_despesas", description="", domain="despesa_municipal")
        result = self.c.normalize(job, items)

        assert result.events[0].value_brl == 50000.0

    def test_normalize_receita(self):
        """Receita → municipality entity + revenue event."""
        items = [RawItem(raw_id="tce_sp_receitas:m0y2024m6:0", data={
            "municipio": "Ribeirão Preto",
            "exercicio": "2024",
            "mes": "6",
            "fonte_receita": "IPTU",
            "valor_arrecadado": "5.000.000,00",
        })]
        job = JobSpec(name="tce_sp_receitas", description="", domain="receita_municipal")
        result = self.c.normalize(job, items)

        assert len(result.entities) == 1
        muni = result.entities[0]
        assert muni.type == "org"
        assert muni.name == "Ribeirão Preto"

        assert len(result.events) == 1
        event = result.events[0]
        assert event.type == "receita_municipal"
        assert event.subtype == "receita"
        assert event.value_brl == 5000000.0
        assert event.attrs["fonte_receita"] == "IPTU"
        assert event.participants[0].role == "org"

    def test_normalize_empty_items(self):
        job = JobSpec(name="tce_sp_despesas", description="", domain="despesa_municipal")
        result = self.c.normalize(job, [])
        assert result.entities == []
        assert result.events == []

    def test_normalize_unknown_job_raises(self):
        job = JobSpec(name="tce_sp_unknown", description="", domain="test")
        with pytest.raises(ValueError, match="Unknown TCE-SP job"):
            self.c.normalize(job, [])
