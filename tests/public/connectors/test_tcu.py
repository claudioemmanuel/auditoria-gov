"""Tests for TCU connector — inidoneos, inabilitados, acordaos."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from openwatch_connectors.base import JobSpec, RateLimitPolicy
from openwatch_connectors.tcu import TCUConnector
from openwatch_models.raw import RawItem


# ── Connector structure ───────────────────────────────────────────────────────


class TestTCUConnector:
    def setup_method(self):
        self.c = TCUConnector()

    def test_name(self):
        assert self.c.name == "tcu"

    def test_has_3_jobs(self):
        assert len(self.c.list_jobs()) == 3

    def test_job_names(self):
        names = {j.name for j in self.c.list_jobs()}
        assert names == {"tcu_inidoneos", "tcu_inabilitados", "tcu_acordaos"}

    def test_all_jobs_enabled(self):
        for job in self.c.list_jobs():
            assert job.enabled is True, f"{job.name} should be enabled"

    def test_rate_limit_policy(self):
        policy = self.c.rate_limit_policy()
        assert isinstance(policy, RateLimitPolicy)
        assert policy.requests_per_second == 5
        assert policy.burst == 10


# ── Normalize ─────────────────────────────────────────────────────────────────


class TestTCUNormalize:
    def setup_method(self):
        self.c = TCUConnector()

    def test_normalize_inidoneo_company(self):
        """CNPJ (14 digits) → type='company', identifiers={'cnpj': '...'}, sancao_tcu event."""
        items = [RawItem(raw_id="tcu_inidoneos:0:0", data={
            "nome": "EMPRESA FRAUDULENTA LTDA",
            "cpf_cnpj": "12345678000199",
            "processo": "TC 001/2023",
            "deliberacao": "Acordao 001/2023 - Plenario",
            "data_transito_julgado": "15/01/2023",
            "data_final": "15/01/2028",
            "data_acordao": "10/01/2023",
            "uf": "DF",
            "municipio": "Brasilia",
        })]
        job = JobSpec(name="tcu_inidoneos", description="", domain="sancao_tcu")
        result = self.c.normalize(job, items)

        assert len(result.entities) == 1
        entity = result.entities[0]
        assert entity.type == "company"
        assert entity.identifiers.get("cnpj") == "12345678000199"
        assert entity.name == "EMPRESA FRAUDULENTA LTDA"

        assert len(result.events) == 1
        event = result.events[0]
        assert event.type == "sancao_tcu"
        assert event.subtype == "inidoneo"
        assert event.participants[0].role == "sanctioned"
        assert event.attrs["uf"] == "DF"

    def test_normalize_inabilitado_person(self):
        """CPF (11 digits) → type='person', identifiers={'cpf': '...'}."""
        items = [RawItem(raw_id="tcu_inabilitados:0:0", data={
            "nome": "JOAO DA SILVA",
            "cpf": "12345678901",
            "processo": "TC 002/2023",
            "deliberacao": "Acordao 002/2023",
            "data_transito_julgado": "20/02/2023",
            "data_final": "20/02/2028",
            "data_acordao": "15/02/2023",
            "uf": "SP",
            "municipio": "Sao Paulo",
        })]
        job = JobSpec(name="tcu_inabilitados", description="", domain="sancao_tcu")
        result = self.c.normalize(job, items)

        assert len(result.entities) == 1
        entity = result.entities[0]
        assert entity.type == "person"
        assert entity.identifiers.get("cpf") == "12345678901"

        assert len(result.events) == 1
        event = result.events[0]
        assert event.subtype == "inabilitado"
        assert event.participants[0].role == "sanctioned"

    def test_normalize_empty_items(self):
        job = JobSpec(name="tcu_inidoneos", description="", domain="sancao_tcu")
        result = self.c.normalize(job, [])
        assert result.entities == []
        assert result.events == []

    def test_normalize_missing_cpf_cnpj(self):
        """Item with no cpf_cnpj → entity with empty identifiers; event still created."""
        items = [RawItem(raw_id="tcu_inidoneos:0:0", data={
            "nome": "ENTIDADE SEM CPF",
            "processo": "TC 003/2023",
            "data_acordao": "01/03/2023",
        })]
        job = JobSpec(name="tcu_inidoneos", description="", domain="sancao_tcu")
        result = self.c.normalize(job, items)

        assert len(result.entities) == 1
        assert len(result.events) == 1
        assert result.entities[0].identifiers == {}

    def test_normalize_acordaos(self):
        items = [RawItem(raw_id="tcu_acordaos:0:0", data={
            "key": "TC-001/2023",
            "tipo": "ACORDAO",
            "anoAcordao": "2023",
            "titulo": "Fiscalizacao de obras",
            "numeroAcordao": "1234",
            "colegiado": "Plenario",
            "dataSessao": "2023-01-10",
            "relator": "Min. Fulano",
            "situacao": "aprovado",
            "sumario": "Fiscalizacao...",
            "urlAcordao": "https://contas.tcu.gov.br/acordao/1234",
        })]
        job = JobSpec(name="tcu_acordaos", description="", domain="acordao_tcu")
        result = self.c.normalize(job, items)

        assert len(result.events) == 1
        event = result.events[0]
        assert event.type == "acordao_tcu"
        assert event.description == "Fiscalizacao de obras"
        assert event.attrs["numero"] == "1234"
        assert event.attrs["colegiado"] == "Plenario"
        assert event.attrs["relator"] == "Min. Fulano"
        assert event.attrs["url_acordao"] == "https://contas.tcu.gov.br/acordao/1234"
        # No entities for acordaos
        assert result.entities == []

    def test_normalize_unknown_job_raises(self):
        job = JobSpec(name="tcu_unknown", description="", domain="test")
        with pytest.raises(ValueError, match="Unknown TCU job"):
            self.c.normalize(job, [])

    def test_normalize_date_iso_format(self):
        """Connector accepts ISO date strings as well as DD/MM/YYYY."""
        items = [RawItem(raw_id="tcu_inidoneos:0:0", data={
            "nome": "EMPRESA TESTE",
            "cpf_cnpj": "12345678000199",
            "data_transito_julgado": "2023-01-15",
            "data_final": "2028-01-15",
            "data_acordao": "2023-01-10",
        })]
        job = JobSpec(name="tcu_inidoneos", description="", domain="sancao_tcu")
        result = self.c.normalize(job, items)

        event = result.events[0]
        assert event.occurred_at is not None
        assert event.occurred_at.year == 2023
        assert event.attrs["sanction_start"] is not None
        assert event.attrs["sanction_end"] is not None

    def test_normalize_missing_data_final_sets_none_sanction_end(self):
        """No data_final → sanction_end attr is None (indefinite sanction)."""
        items = [RawItem(raw_id="tcu_inidoneos:0:0", data={
            "nome": "EMPRESA INDEFINIDA",
            "cpf_cnpj": "12345678000199",
            "data_transito_julgado": "15/01/2023",
            "data_acordao": "10/01/2023",
        })]
        job = JobSpec(name="tcu_inidoneos", description="", domain="sancao_tcu")
        result = self.c.normalize(job, items)
        assert result.events[0].attrs["sanction_end"] is None

    def test_normalize_participant_entity_reference(self):
        """Event participant entity_ref matches the created entity."""
        items = [RawItem(raw_id="tcu_inidoneos:0:0", data={
            "nome": "EMPRESA REF",
            "cpf_cnpj": "12345678000199",
        })]
        job = JobSpec(name="tcu_inidoneos", description="", domain="sancao_tcu")
        result = self.c.normalize(job, items)

        participant_entity = result.events[0].participants[0].entity_ref
        assert participant_entity.name == "EMPRESA REF"
        assert participant_entity.identifiers.get("cnpj") == "12345678000199"


# ── Fetch ─────────────────────────────────────────────────────────────────────


class TestTCUFetch:
    def setup_method(self):
        self.c = TCUConnector()

    def _make_mock_client(self, response_data):
        mock_resp = MagicMock()
        mock_resp.json.return_value = response_data
        mock_resp.raise_for_status = MagicMock()
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        return mock_client

    @pytest.mark.asyncio
    async def test_fetch_inidoneos_partial_page_no_next_cursor(self):
        data = {"items": [{"nome": "Empresa X", "cpf_cnpj": "12345678000199"}]}
        mock_client = self._make_mock_client(data)
        with patch("openwatch_connectors.tcu.tcu_contas_client", return_value=mock_client):
            job = JobSpec(name="tcu_inidoneos", description="", domain="sancao_tcu")
            items, next_cursor = await self.c.fetch(job)
        assert len(items) == 1
        assert next_cursor is None  # 1 < 100

    @pytest.mark.asyncio
    async def test_fetch_inidoneos_full_page_returns_cursor(self):
        data = {"items": [{"nome": f"Empresa {i}"} for i in range(100)]}
        mock_client = self._make_mock_client(data)
        with patch("openwatch_connectors.tcu.tcu_contas_client", return_value=mock_client):
            job = JobSpec(name="tcu_inidoneos", description="", domain="sancao_tcu")
            items, next_cursor = await self.c.fetch(job)
        assert len(items) == 100
        assert next_cursor == "100"

    @pytest.mark.asyncio
    async def test_fetch_inabilitados_partial_page(self):
        data = {"items": [{"nome": "Pessoa Y", "cpf": "12345678901"}]}
        mock_client = self._make_mock_client(data)
        with patch("openwatch_connectors.tcu.tcu_contas_client", return_value=mock_client):
            job = JobSpec(name="tcu_inabilitados", description="", domain="sancao_tcu")
            items, next_cursor = await self.c.fetch(job)
        assert len(items) == 1
        assert next_cursor is None

    @pytest.mark.asyncio
    async def test_fetch_acordaos_partial_page(self):
        data = [{"key": "TC-001/2023", "titulo": "Fiscalizacao"}]
        mock_client = self._make_mock_client(data)
        with patch("openwatch_connectors.tcu.tcu_dados_client", return_value=mock_client):
            job = JobSpec(name="tcu_acordaos", description="", domain="acordao_tcu")
            items, next_cursor = await self.c.fetch(job)
        assert len(items) == 1
        assert next_cursor is None  # 1 < 50

    @pytest.mark.asyncio
    async def test_fetch_acordaos_full_page_returns_cursor(self):
        data = [{"key": f"TC-{i}/2023"} for i in range(50)]
        mock_client = self._make_mock_client(data)
        with patch("openwatch_connectors.tcu.tcu_dados_client", return_value=mock_client):
            job = JobSpec(name="tcu_acordaos", description="", domain="acordao_tcu")
            items, next_cursor = await self.c.fetch(job)
        assert len(items) == 50
        assert next_cursor == "50"

    @pytest.mark.asyncio
    async def test_fetch_with_cursor_passes_offset(self):
        data = {"items": [{"nome": "Empresa Z"}]}
        mock_client = self._make_mock_client(data)
        with patch("openwatch_connectors.tcu.tcu_contas_client", return_value=mock_client):
            job = JobSpec(name="tcu_inidoneos", description="", domain="sancao_tcu")
            items, next_cursor = await self.c.fetch(job, cursor="200")
        assert len(items) == 1
        call_kwargs = mock_client.get.call_args
        assert call_kwargs[1]["params"]["offset"] == 200

    @pytest.mark.asyncio
    async def test_fetch_unknown_job_raises(self):
        job = JobSpec(name="tcu_unknown", description="", domain="test")
        with pytest.raises(ValueError, match="Unknown TCU job"):
            await self.c.fetch(job)

    @pytest.mark.asyncio
    async def test_fetch_inidoneos_empty_response(self):
        data = {"items": []}
        mock_client = self._make_mock_client(data)
        with patch("openwatch_connectors.tcu.tcu_contas_client", return_value=mock_client):
            job = JobSpec(name="tcu_inidoneos", description="", domain="sancao_tcu")
            items, next_cursor = await self.c.fetch(job)
        assert items == []
        assert next_cursor is None
