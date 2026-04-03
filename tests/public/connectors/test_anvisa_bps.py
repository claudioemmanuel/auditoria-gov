"""Tests for ANVISA/BPS connector — prices and drug registry."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from openwatch_connectors.anvisa_bps import AnvisaBPSConnector, _next_bps_cursor
from openwatch_connectors.base import JobSpec, RateLimitPolicy, SourceClassification
from openwatch_models.raw import RawItem


class TestAnvisaBPSConnector:
    def setup_method(self):
        self.c = AnvisaBPSConnector()

    def test_name(self):
        assert self.c.name == "anvisa_bps"

    def test_has_2_jobs(self):
        assert len(self.c.list_jobs()) == 2

    def test_job_names(self):
        names = {j.name for j in self.c.list_jobs()}
        assert names == {"anvisa_bps_prices", "anvisa_bulario_registry"}

    def test_jobs_enabled(self):
        for job in self.c.list_jobs():
            assert job.enabled is True

    def test_classification_is_enrichment_only(self):
        assert self.c.classification == SourceClassification.ENRICHMENT_ONLY

    def test_rate_limit_policy(self):
        policy = self.c.rate_limit_policy()
        assert isinstance(policy, RateLimitPolicy)
        assert policy.requests_per_second == 1
        assert policy.burst == 1


class TestAnvisaBPSNormalize:
    def setup_method(self):
        self.c = AnvisaBPSConnector()

    def test_normalize_bps_with_cnpj_and_value_fallback(self):
        items = [
            RawItem(
                raw_id="anvisa_bps_prices:0",
                data={
                    "cnpj_do_fornecedor": "12.345.678/0001-95",
                    "nome_do_fornecedor": "Fornecedor Saúde SA",
                    "cnpj_instituicao": "11.444.777/0001-61",
                    "nome_instituicao": "Secretaria Municipal de Saúde",
                    "quantidade": "10",
                    "preco_unitario": "25,50",
                    "catmat": "12345",
                    "descricao_catmat": "Dipirona 500mg",
                    "modalidade": "Pregão",
                    "tipo_compra": "Ordinária",
                    "uf": "SP",
                    "municipio": "Campinas",
                    "generico": "Sim",
                },
            )
        ]
        job = JobSpec(name="anvisa_bps_prices", description="", domain="health_procurement")
        result = self.c.normalize(job, items)

        assert len(result.entities) == 2
        supplier = next(e for e in result.entities if e.type == "company")
        assert supplier.identifiers["cnpj"] == "12345678000195"
        buyer = next(e for e in result.entities if e.type == "org")
        assert buyer.identifiers["cnpj"] == "11444777000161"

        assert len(result.events) == 1
        event = result.events[0]
        assert event.type == "health_procurement"
        assert event.subtype == "medicine_purchase"
        assert event.value_brl == 255.0
        assert event.attrs["catmat"] == "12345"
        assert event.attrs["descricao_catmat"] == "Dipirona 500mg"
        assert event.attrs["generico"] is True
        roles = {p.role for p in event.participants}
        assert {"supplier", "buyer"} <= roles

    def test_normalize_bulario_with_attrs(self):
        items = [
            RawItem(
                raw_id="anvisa_bulario_registry:25351000123202400",
                data={
                    "numero_processo": "25351000123202400",
                    "numero_registro": "123456789",
                    "principio_ativo": "Paracetamol",
                    "categoria_regulatoria": "Genérico",
                    "data_vencimento_registro": "2030-12-31",
                    "cnpj_fabricante": "11.222.333/0001-81",
                    "nome_empresa": "Farmacêutica Exemplo Ltda",
                },
            )
        ]
        job = JobSpec(name="anvisa_bulario_registry", description="", domain="regulatory_record")
        result = self.c.normalize(job, items)

        assert len(result.entities) == 1
        company = result.entities[0]
        assert company.type == "company"
        assert company.identifiers["cnpj"] == "11222333000181"

        assert len(result.events) == 1
        event = result.events[0]
        assert event.type == "regulatory_record"
        assert event.subtype == "anvisa_drug_registration"
        assert event.attrs["numero_registro"] == "123456789"
        assert event.attrs["principio_ativo"] == "Paracetamol"
        assert event.attrs["categoria_regulatoria"] == "Genérico"
        assert event.attrs["data_vencimento_registro"] == "2030-12-31"
        assert event.attrs["numero_processo"] == "25351000123202400"

    def test_normalize_empty_input(self):
        job = JobSpec(name="anvisa_bps_prices", description="", domain="health_procurement")
        result = self.c.normalize(job, [])
        assert result.entities == []
        assert result.events == []

    def test_normalize_unknown_job_raises(self):
        job = JobSpec(name="anvisa_unknown", description="", domain="test")
        with pytest.raises(ValueError, match="Unknown ANVISA/BPS job"):
            self.c.normalize(job, [])


class TestAnvisaBPSPagination:
    def test_bps_next_cursor_when_full_page(self):
        assert _next_bps_cursor(offset=0, page_size=200, returned_count=200) == "200"

    def test_bps_next_cursor_when_last_page(self):
        assert _next_bps_cursor(offset=200, page_size=200, returned_count=50) is None


class TestAnvisaBPSFetch:
    def setup_method(self):
        self.c = AnvisaBPSConnector()

    def _make_response(self, payload):
        resp = MagicMock()
        resp.json.return_value = payload
        resp.raise_for_status = MagicMock()
        return resp

    @pytest.mark.asyncio
    async def test_fetch_bps_uses_offset_cursor(self):
        mock_client = AsyncMock()
        mock_client.get.return_value = self._make_response({"bps": [{"id": 1}]})
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("openwatch_connectors.anvisa_bps.anvisa_bps_client", return_value=mock_client):
            job = JobSpec(name="anvisa_bps_prices", description="", domain="health_procurement")
            items, next_cursor = await self.c.fetch(job, cursor="200", params={"limit": 1})
        assert len(items) == 1
        assert items[0].raw_id == "anvisa_bps_prices:200"
        assert next_cursor == "201"

    @pytest.mark.asyncio
    async def test_fetch_bulario_one_page_without_hints(self):
        mock_client = AsyncMock()
        mock_client.get.return_value = self._make_response(
            [{"numero_processo": "25351000123202400"}]
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("openwatch_connectors.anvisa_bps.anvisa_bulario_client", return_value=mock_client):
            job = JobSpec(name="anvisa_bulario_registry", description="", domain="regulatory_record")
            items, next_cursor = await self.c.fetch(job, params={"nome": "Dipirona"})
        assert len(items) == 1
        assert next_cursor is None

    @pytest.mark.asyncio
    async def test_fetch_unknown_job_raises(self):
        job = JobSpec(name="anvisa_unknown", description="", domain="test")
        with pytest.raises(ValueError, match="Unknown ANVISA/BPS job"):
            await self.c.fetch(job)
