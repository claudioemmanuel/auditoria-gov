"""Tests for IBGE connector — municipios, cnae, enrichment-only classification."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from openwatch_connectors.base import JobSpec, RateLimitPolicy, SourceClassification
from openwatch_connectors.ibge import IBGEConnector
from openwatch_models.raw import RawItem


# ── Connector structure ───────────────────────────────────────────────────────


class TestIBGEConnector:
    def setup_method(self):
        self.c = IBGEConnector()

    def test_name(self):
        assert self.c.name == "ibge"

    def test_has_2_jobs(self):
        assert len(self.c.list_jobs()) == 2

    def test_job_names(self):
        names = {j.name for j in self.c.list_jobs()}
        assert names == {"ibge_municipios", "ibge_cnae"}

    def test_all_jobs_enabled(self):
        for job in self.c.list_jobs():
            assert job.enabled is True

    def test_classification_is_enrichment_only(self):
        assert self.c.classification == SourceClassification.ENRICHMENT_ONLY

    def test_jobs_do_not_support_incremental(self):
        for job in self.c.list_jobs():
            assert job.supports_incremental is False

    def test_rate_limit_policy(self):
        policy = self.c.rate_limit_policy()
        assert isinstance(policy, RateLimitPolicy)
        assert policy.requests_per_second == 5


# ── Normalize ─────────────────────────────────────────────────────────────────


class TestIBGENormalize:
    def setup_method(self):
        self.c = IBGEConnector()

    def test_normalize_municipios(self):
        items = [RawItem(raw_id="ibge_municipios:5300108", data={
            "id": 5300108,
            "nome": "Brasilia",
            "microrregiao": {
                "id": 53001,
                "nome": "Brasilia",
                "mesorregiao": {
                    "id": 5301,
                    "nome": "DF",
                    "UF": {
                        "id": 53,
                        "sigla": "DF",
                        "nome": "Distrito Federal",
                        "regiao": {"id": 5, "sigla": "CO", "nome": "Centro-Oeste"},
                    },
                },
            },
        })]
        job = JobSpec(name="ibge_municipios", description="", domain="referencia")
        result = self.c.normalize(job, items)

        assert len(result.entities) == 1
        e = result.entities[0]
        assert e.type == "municipio"
        assert e.name == "Brasilia"
        assert e.identifiers.get("ibge_code") == "5300108"
        assert e.identifiers.get("uf") == "DF"
        # Enrichment source — no events
        assert result.events == []

    def test_normalize_municipios_regional_attrs(self):
        """Municipality entity carries full regional hierarchy in attrs."""
        items = [RawItem(raw_id="ibge_municipios:3550308", data={
            "id": 3550308,
            "nome": "Sao Paulo",
            "microrregiao": {
                "id": 35061,
                "nome": "Sao Paulo",
                "mesorregiao": {
                    "id": 3513,
                    "nome": "Metropolitana de Sao Paulo",
                    "UF": {
                        "id": 35,
                        "sigla": "SP",
                        "nome": "Sao Paulo",
                        "regiao": {"id": 3, "sigla": "SE", "nome": "Sudeste"},
                    },
                },
            },
        })]
        job = JobSpec(name="ibge_municipios", description="", domain="referencia")
        result = self.c.normalize(job, items)
        e = result.entities[0]
        assert e.attrs["uf_nome"] == "Sao Paulo"
        assert e.attrs["regiao_sigla"] == "SE"
        assert e.attrs["microrregiao"] == "Sao Paulo"

    def test_normalize_cnae_section(self):
        items = [RawItem(raw_id="ibge_cnae:secao:A", data={
            "_type": "secao",
            "id": "A",
            "descricao": "Agricultura, pecuaria, producao florestal, pesca e aquicultura",
        })]
        job = JobSpec(name="ibge_cnae", description="", domain="referencia")
        result = self.c.normalize(job, items)

        assert len(result.entities) == 1
        e = result.entities[0]
        assert e.type == "cnae_section"
        assert e.identifiers.get("cnae_secao") == "A"
        assert "Agricultura" in e.name
        assert result.events == []

    def test_normalize_cnae_division(self):
        items = [RawItem(raw_id="ibge_cnae:divisao:01", data={
            "_type": "divisao",
            "id": "01",
            "descricao": "Agricultura, pecuaria e servicos relacionados",
        })]
        job = JobSpec(name="ibge_cnae", description="", domain="referencia")
        result = self.c.normalize(job, items)

        assert len(result.entities) == 1
        e = result.entities[0]
        assert e.type == "cnae_divisao"
        assert e.identifiers.get("cnae_divisao") == "01"

    def test_normalize_empty(self):
        job = JobSpec(name="ibge_municipios", description="", domain="referencia")
        result = self.c.normalize(job, [])
        assert result.entities == []
        assert result.events == []

    def test_normalize_unknown_job_raises(self):
        job = JobSpec(name="ibge_unknown", description="", domain="test")
        with pytest.raises(ValueError, match="Unknown IBGE job"):
            self.c.normalize(job, [])

    def test_normalize_municipio_source_connector(self):
        items = [RawItem(raw_id="ibge_municipios:1100015", data={
            "id": 1100015,
            "nome": "Alta Floresta D'Oeste",
            "microrregiao": {
                "id": 11003,
                "nome": "Cacoal",
                "mesorregiao": {
                    "id": 1102,
                    "nome": "Leste Rondoniense",
                    "UF": {
                        "id": 11,
                        "sigla": "RO",
                        "nome": "Rondonia",
                        "regiao": {"id": 1, "sigla": "N", "nome": "Norte"},
                    },
                },
            },
        })]
        job = JobSpec(name="ibge_municipios", description="", domain="referencia")
        result = self.c.normalize(job, items)
        e = result.entities[0]
        assert e.source_connector == "ibge"
        assert e.source_id == "1100015"


# ── Fetch ─────────────────────────────────────────────────────────────────────


class TestIBGEFetch:
    def setup_method(self):
        self.c = IBGEConnector()

    def _make_resp(self, data):
        resp = MagicMock()
        resp.json.return_value = data
        resp.raise_for_status = MagicMock()
        return resp

    @pytest.mark.asyncio
    async def test_fetch_municipios_returns_all_items(self):
        records = [
            {"id": 5300108, "nome": "Brasilia"},
            {"id": 3550308, "nome": "Sao Paulo"},
        ]
        mock_client = AsyncMock()
        mock_client.get.return_value = self._make_resp(records)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("openwatch_connectors.ibge.ibge_client", return_value=mock_client):
            job = JobSpec(name="ibge_municipios", description="", domain="referencia")
            items, next_cursor = await self.c.fetch(job)
        assert len(items) == 2
        assert next_cursor is None

    @pytest.mark.asyncio
    async def test_fetch_municipios_with_cursor_returns_empty(self):
        """Cursor set means already fetched — returns empty."""
        job = JobSpec(name="ibge_municipios", description="", domain="referencia")
        items, next_cursor = await self.c.fetch(job, cursor="done")
        assert items == []
        assert next_cursor is None

    @pytest.mark.asyncio
    async def test_fetch_cnae_returns_sections_and_divisions(self):
        sections = [{"id": "A", "descricao": "Agricultura"}]
        divisions = [{"id": "01", "descricao": "Agricultura servicos"}]

        mock_client = AsyncMock()
        mock_client.get.side_effect = [
            self._make_resp(sections),
            self._make_resp(divisions),
        ]
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("openwatch_connectors.ibge.ibge_client", return_value=mock_client):
            job = JobSpec(name="ibge_cnae", description="", domain="referencia")
            items, next_cursor = await self.c.fetch(job)
        assert len(items) == 2
        assert next_cursor is None
        raw_ids = {i.raw_id for i in items}
        assert "ibge_cnae:secao:A" in raw_ids
        assert "ibge_cnae:divisao:01" in raw_ids

    @pytest.mark.asyncio
    async def test_fetch_cnae_with_cursor_returns_empty(self):
        job = JobSpec(name="ibge_cnae", description="", domain="referencia")
        items, next_cursor = await self.c.fetch(job, cursor="done")
        assert items == []
        assert next_cursor is None

    @pytest.mark.asyncio
    async def test_fetch_unknown_job_raises(self):
        job = JobSpec(name="ibge_unknown", description="", domain="test")
        with pytest.raises(ValueError, match="Unknown IBGE job"):
            await self.c.fetch(job)

    @pytest.mark.asyncio
    async def test_fetch_municipios_skips_records_without_id(self):
        records = [
            {"id": 5300108, "nome": "Brasilia"},
            {"nome": "Sem ID"},  # missing id — should be skipped
        ]
        mock_client = AsyncMock()
        mock_client.get.return_value = self._make_resp(records)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("openwatch_connectors.ibge.ibge_client", return_value=mock_client):
            job = JobSpec(name="ibge_municipios", description="", domain="referencia")
            items, _ = await self.c.fetch(job)
        assert len(items) == 1
        assert items[0].raw_id == "ibge_municipios:5300108"
