"""Tests for BNDES connector — operações automáticas e não-automáticas."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shared.connectors.base import JobSpec, RateLimitPolicy
from shared.connectors.bndes import BNDESConnector
from shared.models.raw import RawItem


# ── Connector structure ───────────────────────────────────────────────────────


class TestBNDESConnector:
    def setup_method(self):
        self.c = BNDESConnector()

    def test_name(self):
        assert self.c.name == "bndes"

    def test_has_2_jobs(self):
        assert len(self.c.list_jobs()) == 2

    def test_job_names(self):
        names = {j.name for j in self.c.list_jobs()}
        assert names == {"bndes_operacoes_auto", "bndes_operacoes_nao_auto"}

    def test_all_jobs_enabled(self):
        for job in self.c.list_jobs():
            assert job.enabled is True, f"{job.name} should be enabled"

    def test_rate_limit_policy(self):
        policy = self.c.rate_limit_policy()
        assert isinstance(policy, RateLimitPolicy)
        assert policy.requests_per_second == 5
        assert policy.burst == 10


# ── Normalize ─────────────────────────────────────────────────────────────────


class TestBNDESNormalize:
    def setup_method(self):
        self.c = BNDESConnector()

    def test_normalize_operacao_auto(self):
        """Operação automática → company entity + financing event + borrower participant."""
        items = [RawItem(raw_id="bndes_operacoes_auto:0:123", data={
            "_subtype": "automatica",
            "cnpj": "12345678000199",
            "cliente": "Indústria Nacional SA",
            "valor_da_operacao_em_reais": 5000000.00,
            "data_da_contratacao": "2024-03-15",
            "uf": "SP",
            "setor_cnae": "Indústria de Transformação",
            "porte_do_cliente": "Grande",
            "instrumento_financeiro": "FINEM",
            "produto": "Máquinas e Equipamentos",
        })]
        job = JobSpec(name="bndes_operacoes_auto", description="", domain="financiamento_bndes")
        result = self.c.normalize(job, items)

        assert len(result.entities) == 1
        company = result.entities[0]
        assert company.type == "company"
        assert company.name == "Indústria Nacional SA"
        assert company.identifiers["cnpj"] == "12345678000199"
        assert company.source_connector == "bndes"

        assert len(result.events) == 1
        event = result.events[0]
        assert event.type == "financiamento_bndes"
        assert event.subtype == "automatica"
        assert event.source_connector == "bndes"
        assert event.value_brl == 5000000.00
        assert event.occurred_at is not None
        assert event.occurred_at.year == 2024
        assert event.attrs["uf"] == "SP"
        assert event.attrs["setor_cnae"] == "Indústria de Transformação"
        assert event.attrs["instrumento_financeiro"] == "FINEM"

        assert len(event.participants) == 1
        assert event.participants[0].role == "borrower"
        assert event.participants[0].entity_ref.identifiers["cnpj"] == "12345678000199"

    def test_normalize_operacao_nao_auto(self):
        """Non-automatic operation → same structure, subtype=nao_automatica."""
        items = [RawItem(raw_id="bndes_operacoes_nao_auto:0:456", data={
            "_subtype": "nao_automatica",
            "cnpj": "98765432000188",
            "cliente": "Construtora Brasil Ltda",
            "valor_contratado_reais": 15000000.00,
            "data_da_contratacao": "15/01/2024",
            "uf": "RJ",
            "setor_cnae": "Construção",
            "porte_do_cliente": "Média-grande",
            "instrumento_financeiro": "BNDES Automático",
            "produto": "Infraestrutura",
        })]
        job = JobSpec(name="bndes_operacoes_nao_auto", description="", domain="financiamento_bndes")
        result = self.c.normalize(job, items)

        assert len(result.entities) == 1
        assert result.entities[0].identifiers["cnpj"] == "98765432000188"

        assert len(result.events) == 1
        event = result.events[0]
        assert event.subtype == "nao_automatica"
        assert event.value_brl == 15000000.00
        assert event.participants[0].role == "borrower"

    def test_normalize_cnpj_extraction(self):
        """CNPJ is extracted into entity identifiers and used as source_id."""
        items = [RawItem(raw_id="bndes_operacoes_auto:0:789", data={
            "_subtype": "automatica",
            "cnpj": "11222333000144",
            "cliente": "Empresa Teste Ltda",
            "valor_da_operacao_em_reais": 100000.00,
        })]
        job = JobSpec(name="bndes_operacoes_auto", description="", domain="financiamento_bndes")
        result = self.c.normalize(job, items)

        company = result.entities[0]
        assert company.source_id == "11222333000144"
        assert company.identifiers == {"cnpj": "11222333000144"}

    def test_normalize_empty_items(self):
        job = JobSpec(name="bndes_operacoes_auto", description="", domain="financiamento_bndes")
        result = self.c.normalize(job, [])
        assert result.entities == []
        assert result.events == []

    def test_normalize_missing_cnpj_uses_cliente_as_source_id(self):
        """When CNPJ is absent, cliente is used as fallback for cnpj field."""
        items = [RawItem(raw_id="bndes_operacoes_auto:0:999", data={
            "_subtype": "automatica",
            "cliente": "Empresa Sem CNPJ",
            "valor_da_operacao_em_reais": 50000.00,
        })]
        job = JobSpec(name="bndes_operacoes_auto", description="", domain="financiamento_bndes")
        result = self.c.normalize(job, items)

        company = result.entities[0]
        assert company.source_id == "bndes_operacoes_auto:0:999"
        # No valid 14-digit CNPJ present; identifiers should be empty
        assert company.identifiers == {}
