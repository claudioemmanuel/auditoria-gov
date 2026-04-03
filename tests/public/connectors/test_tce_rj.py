"""Tests for TCE-RJ connector — licitações, contratos, penalidades."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from openwatch_connectors.base import JobSpec, RateLimitPolicy
from openwatch_connectors.tce_rj import TCERJConnector
from openwatch_models.raw import RawItem


# ── Connector structure ───────────────────────────────────────────────────────


class TestTCERJConnector:
    def setup_method(self):
        self.c = TCERJConnector()

    def test_name(self):
        assert self.c.name == "tce_rj"

    def test_has_3_jobs(self):
        assert len(self.c.list_jobs()) == 3

    def test_job_names(self):
        names = {j.name for j in self.c.list_jobs()}
        assert names == {"tce_rj_licitacoes", "tce_rj_contratos", "tce_rj_penalidades"}

    def test_all_jobs_enabled(self):
        for job in self.c.list_jobs():
            assert job.enabled is True, f"{job.name} should be enabled"

    def test_rate_limit_policy(self):
        policy = self.c.rate_limit_policy()
        assert isinstance(policy, RateLimitPolicy)
        assert policy.requests_per_second == 5
        assert policy.burst == 10


# ── Normalize ─────────────────────────────────────────────────────────────────


class TestTCERJNormalize:
    def setup_method(self):
        self.c = TCERJConnector()

    def test_normalize_licitacao(self):
        """Licitação → procuring_entity org + supplier + licitacao event."""
        items = [RawItem(raw_id="tce_rj_licitacoes:0:0", data={
            "cnpj_orgao": "12345678000199",
            "orgao": "Prefeitura de Niterói",
            "cnpj_licitante": "98765432000188",
            "licitante": "Construtora ABC Ltda",
            "valorEstimado": 1500000.50,
            "objeto": "Construção de escola municipal",
            "dataAbertura": "15/03/2024",
            "modalidade": "Pregão Eletrônico",
            "exercicio": "2024",
            "municipio": "Niterói",
            "numero_licitacao": "PE-001/2024",
        })]
        job = JobSpec(name="tce_rj_licitacoes", description="", domain="licitacao")
        result = self.c.normalize(job, items)

        assert len(result.entities) == 2
        buyer = result.entities[0]
        assert buyer.type == "org"
        assert buyer.identifiers["cnpj"] == "12345678000199"
        assert buyer.name == "Prefeitura de Niterói"

        supplier = result.entities[1]
        assert supplier.identifiers["cnpj"] == "98765432000188"

        assert len(result.events) == 1
        event = result.events[0]
        assert event.type == "licitacao"
        assert event.source_connector == "tce_rj"
        assert event.value_brl == 1500000.50
        assert event.description == "Construção de escola municipal"
        assert event.attrs["modalidade"] == "Pregão Eletrônico"
        assert event.attrs["municipio"] == "Niterói"
        assert len(event.participants) == 2
        assert event.participants[0].role == "procuring_entity"
        assert event.participants[1].role == "supplier"

    def test_normalize_contrato(self):
        """Contrato → buyer + supplier entities, contrato event."""
        items = [RawItem(raw_id="tce_rj_contratos:0:0", data={
            "cnpj_orgao": "33000167000101",
            "orgao": "Secretaria de Saúde",
            "fornecedor_cnpj": "11222333000144",
            "fornecedor_nome": "MedSupply Ltda",
            "valor": 250000.00,
            "objeto": "Fornecimento de medicamentos",
            "vigencia_inicio": "2024-01-01",
            "vigencia_fim": "2024-12-31",
            "numero_contrato": "CT-042/2024",
            "municipio": "Rio de Janeiro",
            "exercicio": "2024",
        })]
        job = JobSpec(name="tce_rj_contratos", description="", domain="contrato")
        result = self.c.normalize(job, items)

        assert len(result.entities) == 2
        buyer = result.entities[0]
        assert buyer.type == "org"
        assert buyer.identifiers["cnpj"] == "33000167000101"
        assert buyer.name == "Secretaria de Saúde"

        supplier = result.entities[1]
        assert supplier.identifiers["cnpj"] == "11222333000144"
        assert supplier.name == "MedSupply Ltda"

        assert len(result.events) == 1
        event = result.events[0]
        assert event.type == "contrato"
        assert event.value_brl == 250000.00
        assert event.attrs["numero_contrato"] == "CT-042/2024"
        assert event.attrs["vigencia_inicio"] is not None
        assert event.attrs["vigencia_fim"] is not None
        assert len(event.participants) == 2
        assert event.participants[0].role == "buyer"
        assert event.participants[1].role == "supplier"

    def test_normalize_penalidade_company_cnpj(self):
        """CNPJ (14 digits) → type='company', identifiers={'cnpj': '...'}."""
        items = [RawItem(raw_id="tce_rj_penalidades:0:0", data={
            "cpf_cnpj": "12345678000199",
            "nome": "Empresa Penalizada SA",
            "tipo_penalidade": "Multa",
            "descricao": "Descumprimento contratual",
            "data_publicacao": "10/05/2024",
            "processo": "PROC-123/2024",
            "municipio": "Petrópolis",
        })]
        job = JobSpec(name="tce_rj_penalidades", description="", domain="penalidade_tce_rj")
        result = self.c.normalize(job, items)

        assert len(result.entities) == 1
        entity = result.entities[0]
        assert entity.type == "company"
        assert entity.identifiers["cnpj"] == "12345678000199"
        assert entity.name == "Empresa Penalizada SA"

        assert len(result.events) == 1
        event = result.events[0]
        assert event.type == "penalidade_tce_rj"
        assert event.subtype == "Multa"
        assert event.participants[0].role == "sanctioned"

    def test_normalize_penalidade_person_cpf(self):
        """CPF (11 digits) → type='person', identifiers={'cpf': '...'}."""
        items = [RawItem(raw_id="tce_rj_penalidades:0:0", data={
            "cpf_cnpj": "12345678901",
            "nome": "João da Silva",
            "tipo_penalidade": "Inabilitação",
            "data_publicacao": "2024-03-20",
            "processo": "PROC-456/2024",
            "municipio": "Campos dos Goytacazes",
        })]
        job = JobSpec(name="tce_rj_penalidades", description="", domain="penalidade_tce_rj")
        result = self.c.normalize(job, items)

        assert len(result.entities) == 1
        entity = result.entities[0]
        assert entity.type == "person"
        assert entity.identifiers["cpf"] == "12345678901"

        assert len(result.events) == 1
        assert result.events[0].participants[0].role == "sanctioned"

    def test_normalize_empty_items(self):
        job = JobSpec(name="tce_rj_licitacoes", description="", domain="licitacao")
        result = self.c.normalize(job, [])
        assert result.entities == []
        assert result.events == []

    def test_normalize_unknown_job_raises(self):
        job = JobSpec(name="tce_rj_unknown", description="", domain="test")
        with pytest.raises(ValueError, match="Unknown TCE-RJ job"):
            self.c.normalize(job, [])
