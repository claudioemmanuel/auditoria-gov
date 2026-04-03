"""Tests for BrasilAPI CNPJ enrichment connector."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from openwatch_connectors.base import JobSpec, SourceClassification
from openwatch_connectors.brasilapi_cnpj import BrasilAPICNPJConnector
from openwatch_models.raw import RawItem


class TestBrasilAPICNPJConnector:
    def setup_method(self):
        self.c = BrasilAPICNPJConnector()

    def test_structure_and_job_config(self):
        assert self.c.name == "brasilapi_cnpj"
        assert self.c.classification == SourceClassification.ENRICHMENT_ONLY
        jobs = self.c.list_jobs()
        assert len(jobs) == 1
        assert jobs[0].name == "brasilapi_cnpj_lookup"
        assert jobs[0].supports_incremental is False
        assert jobs[0].enabled is True

    @pytest.mark.asyncio
    async def test_fetch_invalid_cnpj_returns_empty(self):
        job = JobSpec(name="brasilapi_cnpj_lookup", description="", domain="empresa")
        items, next_cursor = await self.c.fetch(job, params={"cnpj": "123"})
        assert items == []
        assert next_cursor is None

    @pytest.mark.asyncio
    async def test_fetch_unknown_job_raises(self):
        job = JobSpec(name="brasilapi_unknown", description="", domain="empresa")
        with pytest.raises(ValueError, match="Unknown BrasilAPI CNPJ job"):
            await self.c.fetch(job, params={"cnpj": "12.345.678/0001-95"})

    @pytest.mark.asyncio
    async def test_fetch_valid_cnpj_builds_deterministic_raw_item(self):
        payload = {
            "cnpj": "12345678000195",
            "razao_social": "Empresa Teste LTDA",
            "descricao_situacao_cadastral": "ATIVA",
        }
        response = MagicMock()
        response.json.return_value = payload
        response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "shared.connectors.brasilapi_cnpj.brasilapi_client",
            return_value=mock_client,
        ):
            job = JobSpec(name="brasilapi_cnpj_lookup", description="", domain="empresa")
            items, next_cursor = await self.c.fetch(job, params={"cnpj": "12.345.678/0001-95"})

        assert next_cursor is None
        assert len(items) == 1
        assert items[0].raw_id == "brasilapi_cnpj_lookup:12345678000195"


class TestBrasilAPICNPJNormalize:
    def setup_method(self):
        self.c = BrasilAPICNPJConnector()

    def test_valid_cnpj_normalize_path_creates_company_and_event(self):
        job = JobSpec(name="brasilapi_cnpj_lookup", description="", domain="empresa")
        items = [
            RawItem(
                raw_id="brasilapi_cnpj_lookup:12345678000195",
                data={
                    "cnpj": "12.345.678/0001-95",
                    "razao_social": "Empresa Teste LTDA",
                    "descricao_situacao_cadastral": "ATIVA",
                    "cnae_fiscal": 6201501,
                    "cnae_fiscal_descricao": "Desenvolvimento de software",
                    "porte": "DEMAIS",
                    "natureza_juridica": "206-2 - Sociedade Empresária Limitada",
                    "capital_social": "150000.00",
                    "logradouro": "Rua Exemplo",
                    "numero": "100",
                    "bairro": "Centro",
                    "cep": "01001000",
                    "uf": "SP",
                    "municipio": "Sao Paulo",
                },
            )
        ]
        result = self.c.normalize(job, items)

        assert len(result.entities) == 1
        assert len(result.events) == 1

        company = result.entities[0]
        assert company.type == "company"
        assert company.identifiers == {"cnpj": "12345678000195"}
        assert company.name == "Empresa Teste LTDA"

        event = result.events[0]
        assert event.type == "company_profile"
        assert event.subtype == "registration_status"
        assert event.attrs["situacao_cadastral"] == "ATIVA"
        assert "6201501" in str(event.attrs["cnae"])
        assert event.attrs["porte"] == "DEMAIS"
        assert event.attrs["natureza_juridica"] == "206-2 - Sociedade Empresária Limitada"
        assert event.attrs["capital_social"] == "150000.00"
        assert event.attrs["endereco"] == "Rua Exemplo, 100, Centro, 01001000"
        assert event.attrs["uf"] == "SP"
        assert event.attrs["municipio"] == "Sao Paulo"
        assert len(event.participants) == 1
        assert event.participants[0].role == "subject"
        assert event.participants[0].entity_ref.identifiers["cnpj"] == "12345678000195"

    def test_normalize_empty_raw_input_safe(self):
        job = JobSpec(name="brasilapi_cnpj_lookup", description="", domain="empresa")
        result = self.c.normalize(job, [])
        assert result.entities == []
        assert result.events == []

    def test_normalize_unknown_job_raises(self):
        with pytest.raises(ValueError, match="Unknown BrasilAPI CNPJ job"):
            self.c.normalize(JobSpec(name="unknown", description="", domain="empresa"), [])
