"""Tests for TCE-PE connector — licitações, contratos, despesas."""

import pytest

from openwatch_connectors.base import JobSpec, RateLimitPolicy
from openwatch_connectors.tce_pe import TCEPEConnector
from openwatch_models.raw import RawItem


class TestTCEPEConnector:
    def setup_method(self):
        self.c = TCEPEConnector()

    def test_name(self):
        assert self.c.name == "tce_pe"

    def test_has_3_jobs(self):
        assert len(self.c.list_jobs()) == 3

    def test_job_names(self):
        names = {j.name for j in self.c.list_jobs()}
        assert names == {"tce_pe_licitacoes", "tce_pe_contratos", "tce_pe_despesas"}

    def test_all_jobs_enabled(self):
        for job in self.c.list_jobs():
            assert job.enabled is True, f"{job.name} should be enabled"

    def test_rate_limit_policy(self):
        policy = self.c.rate_limit_policy()
        assert isinstance(policy, RateLimitPolicy)
        assert policy.requests_per_second == 1
        assert policy.burst == 1


class TestTCEPENormalize:
    def setup_method(self):
        self.c = TCEPEConnector()

    def test_normalize_licitacoes(self):
        items = [RawItem(raw_id="tce_pe_licitacoes:2024:123", data={
            "ANOLICITACAO": "2024",
            "NUMEROLICITACAO": "PE-123/2024",
            "NUMEROPROCESSO": "PROC-999",
            "NOMEUNIDADEGESTORA": "Prefeitura do Recife",
            "MUNICIPIO": "Recife",
            "OBJETOLICITACAO": "Aquisição de merenda escolar",
            "VALORLICITACAO": "1500000,50",
            "CPFCNPJ": "12345678000199",
            "NOMEFORNECEDOR": "Fornecedor A Ltda",
            "DATALICITACAO": "15/03/2024",
            "MODALIDADE": "Pregão",
        })]
        job = JobSpec(name="tce_pe_licitacoes", description="", domain="licitacao")
        result = self.c.normalize(job, items)

        assert len(result.events) == 1
        event = result.events[0]
        assert event.type == "licitacao"
        assert event.subtype == "licitacao"
        assert event.value_brl == 1500000.50
        assert event.attrs["municipio"] == "Recife"
        assert event.attrs["nome_unidade_gestora"] == "Prefeitura do Recife"

        assert len(result.entities) == 3
        supplier = next(e for e in result.entities if e.type == "company")
        assert supplier.identifiers["cnpj"] == "12345678000199"
        roles = {p.role for p in event.participants}
        assert {"procuring_entity", "jurisdiction", "supplier"} <= roles

    def test_normalize_contratos(self):
        items = [RawItem(raw_id="tce_pe_contratos:2024:abc", data={
            "ANOREFERENCIA": "2024",
            "NUMEROCONTRATO": "CT-042/2024",
            "NUMEROPROCESSO": "PROC-2024-42",
            "NOMEUNIDADEGESTORA": "Secretaria de Saúde",
            "MUNICIPIO": "Olinda",
            "OBJETOCONTRATO": "Fornecimento de medicamentos",
            "VALORCONTRATO": "250000,00",
            "CPFCNPJ": "98765432000188",
            "NOMECONTRATADO": "MedSupply Ltda",
            "DATAASSINATURA": "2024-01-10",
        })]
        job = JobSpec(name="tce_pe_contratos", description="", domain="contrato")
        result = self.c.normalize(job, items)

        assert len(result.events) == 1
        event = result.events[0]
        assert event.type == "contrato"
        assert event.subtype == "public_contract"
        assert event.value_brl == 250000.0
        assert event.attrs["numero_contrato"] == "CT-042/2024"

        supplier = next(e for e in result.entities if e.type == "company")
        assert supplier.identifiers["cnpj"] == "98765432000188"
        roles = {p.role for p in event.participants}
        assert {"buyer", "jurisdiction", "supplier"} <= roles

    def test_normalize_despesas(self):
        items = [RawItem(raw_id="tce_pe_despesas:2024:xyz", data={
            "ANOREFERENCIA": "2024",
            "NOMEUNIDADEGESTORA": "Prefeitura de Caruaru",
            "MUNICIPIO": "Caruaru",
            "OBJETODESPESA": "Pagamento de serviços de limpeza",
            "VALORPAGO": "50000,10",
            "NUMEMPENHO": "EMP-001",
            "CPF_CNPJ": "12345678901",
            "NOMEFAVORECIDO": "João da Silva",
            "DATAPAGAMENTO": "2024-06-01",
        })]
        job = JobSpec(name="tce_pe_despesas", description="", domain="despesa_municipal")
        result = self.c.normalize(job, items)

        assert len(result.events) == 1
        event = result.events[0]
        assert event.type == "despesa_municipal"
        assert event.subtype == "municipal_expense"
        assert event.value_brl == 50000.10
        assert event.attrs["numero_empenho"] == "EMP-001"

        person = next(e for e in result.entities if e.type == "person")
        assert person.identifiers["cpf"] == "12345678901"
        roles = {p.role for p in event.participants}
        assert {"responsible_entity", "municipality", "payee"} <= roles

    def test_cnpj_cpf_extraction(self):
        items = [
            RawItem(raw_id="tce_pe_contratos:2024:cnpj", data={
                "CPFCNPJ": "12.345.678/0001-99",
                "NOMECONTRATADO": "Empresa Teste SA",
            }),
            RawItem(raw_id="tce_pe_despesas:2024:cpf", data={
                "CPF_CNPJ": "123.456.789-01",
                "NOMEFAVORECIDO": "Pessoa Teste",
            }),
        ]
        contratos_job = JobSpec(name="tce_pe_contratos", description="", domain="contrato")
        despesas_job = JobSpec(name="tce_pe_despesas", description="", domain="despesa_municipal")

        contratos_result = self.c.normalize(contratos_job, [items[0]])
        despesas_result = self.c.normalize(despesas_job, [items[1]])

        cnpj_entity = next(e for e in contratos_result.entities if e.type == "company")
        assert cnpj_entity.identifiers["cnpj"] == "12345678000199"

        cpf_entity = next(e for e in despesas_result.entities if e.type == "person")
        assert cpf_entity.identifiers["cpf"] == "12345678901"

    def test_normalize_empty_items(self):
        job = JobSpec(name="tce_pe_licitacoes", description="", domain="licitacao")
        result = self.c.normalize(job, [])
        assert result.entities == []
        assert result.events == []

    def test_normalize_unknown_job_raises(self):
        job = JobSpec(name="tce_pe_unknown", description="", domain="test")
        with pytest.raises(ValueError, match="Unknown TCE-PE job"):
            self.c.normalize(job, [])
