"""Tests for all data connectors — registry, structure, normalize, fetch (mocked HTTP)."""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from shared.connectors import ConnectorRegistry, get_connector
from shared.connectors.base import BaseConnector, JobSpec, RateLimitPolicy
from shared.models.raw import RawItem


# ── Registry ──────────────────────────────────────────────────────────

class TestConnectorRegistry:
    def test_has_19_connectors(self):
        assert len(ConnectorRegistry) == 19

    def test_all_keys(self):
        expected = {
            "portal_transparencia", "compras_gov", "comprasnet_contratos",
            "pncp", "transferegov", "camara", "senado", "tse",
            "receita_cnpj", "querido_diario", "orcamento_bim",
            "tcu", "datajud", "ibge",
            "tce_rj", "tce_sp", "jurisprudencia", "bacen", "bndes",
        }
        assert set(ConnectorRegistry.keys()) == expected

    def test_all_are_base_connector_subclasses(self):
        for cls in ConnectorRegistry.values():
            assert issubclass(cls, BaseConnector)


class TestGetConnector:
    def test_valid_name(self):
        c = get_connector("portal_transparencia")
        assert isinstance(c, BaseConnector)
        assert c.name == "portal_transparencia"

    def test_invalid_name(self):
        with pytest.raises(ValueError, match="Unknown connector"):
            get_connector("nonexistent")

    def test_alias_receita_federal_cnpj(self):
        c = get_connector("receita_federal_cnpj")
        assert isinstance(c, BaseConnector)
        assert c.name == "receita_cnpj"


class TestJobSpec:
    def test_defaults(self):
        job = JobSpec(name="test", description="Test job", domain="test")
        assert job.supports_incremental is True
        assert job.enabled is False
        assert job.default_params == {}


class TestRateLimitPolicy:
    def test_defaults(self):
        policy = RateLimitPolicy()
        assert policy.requests_per_second == 5
        assert policy.burst == 10


class TestAllJobsHaveRequiredFields:
    def test_all_jobs_have_name_desc_domain(self):
        for name, cls in ConnectorRegistry.items():
            c = cls()
            for job in c.list_jobs():
                assert job.name, f"{name} has job with empty name"
                assert job.description, f"{name}/{job.name} has empty description"
                assert job.domain, f"{name}/{job.name} has empty domain"


# ── Portal Transparência ────────────────────────────────────────────

class TestPortalTransparencia:
    def setup_method(self):
        self.c = get_connector("portal_transparencia")

    def test_name(self):
        assert self.c.name == "portal_transparencia"

    def test_has_8_jobs(self):
        assert len(self.c.list_jobs()) == 8

    def test_job_names(self):
        names = {j.name for j in self.c.list_jobs()}
        assert "pt_sancoes_ceis_cnep" in names
        assert "pt_servidores_remuneracao" in names

    def test_jobs_enabled_state(self):
        jobs = {j.name: j for j in self.c.list_jobs()}
        # Bulk-fetchable jobs
        assert jobs["pt_sancoes_ceis_cnep"].enabled is True
        assert jobs["pt_emendas"].enabled is True
        assert jobs["pt_viagens"].enabled is True
        assert jobs["pt_convenios_transferencias"].enabled is True
        assert jobs["pt_despesas_execucao"].enabled is True
        assert jobs["pt_cartao_pagamento"].enabled is True
        # Dimension-keyed jobs (iterate per SIAPE organ / IBGE municipality)
        assert jobs["pt_servidores_remuneracao"].enabled is True
        assert jobs["pt_beneficios"].enabled is True

    def test_rate_limit_policy(self):
        policy = self.c.rate_limit_policy()
        assert policy.requests_per_second == 5

    def test_normalize_sancoes(self):
        items = [RawItem(raw_id="pt_sancoes:1:0", data={
            "sancionado": {
                "nome": "EMPRESA FANTASMA LTDA",
                "cnpjCpf": "12345678000199",
                "ufSancionado": "DF",
            },
            "tipoSancao": {"descricaoResumida": "CEIS"},
            "textoPublicacao": "Sanção por fraude",
            "orgaoSancionador": {"nome": "CGU"},
            "dataInicioSancao": "2024-01-01",
            "dataFimSancao": "2025-01-01",
            "fonteSancao": "CEIS",
        })]
        job = JobSpec(name="pt_sancoes_ceis_cnep", description="", domain="sancao")
        result = self.c.normalize(job, items)
        # 2 entities: sanctioned company + sanctioning body (CGU)
        assert len(result.entities) == 2
        names = {e.name for e in result.entities}
        assert "EMPRESA FANTASMA LTDA" in names
        assert "CGU" in names
        sanctioned = next(e for e in result.entities if e.name == "EMPRESA FANTASMA LTDA")
        assert sanctioned.type == "company"
        assert sanctioned.identifiers["cnpj"] == "12345678000199"
        assert len(result.events) == 1
        assert result.events[0].type == "sancao"
        assert result.events[0].participants[0].role == "sanctioned"

    def test_normalize_sancoes_extracts_identifier_from_codigo_formatado(self):
        items = [
            RawItem(
                raw_id="pt_sancoes:2:0",
                data={
                    "sancionado": {
                        "nome": "EMPRESA TESTE LTDA",
                        "codigoFormatado": "12.345.678/0001-99",
                    },
                    "tipoSancao": {"descricaoResumida": "CEIS"},
                    "textoPublicacao": "Sanção por fraude",
                    "orgaoSancionador": {"nome": "CGU"},
                    "dataInicioSancao": "2024-01-01",
                },
            ),
            RawItem(
                raw_id="pt_sancoes:2:1",
                data={
                    "sancionado": {
                        "nome": "JOAO DA SILVA",
                        "codigoFormatado": "215.768.058-67",
                    },
                    "tipoSancao": {"descricaoResumida": "CEIS"},
                    "textoPublicacao": "Sanção por fraude",
                    "orgaoSancionador": {"nome": "CGU"},
                    "dataInicioSancao": "2024-01-01",
                },
            ),
        ]
        job = JobSpec(name="pt_sancoes_ceis_cnep", description="", domain="sancao")
        result = self.c.normalize(job, items)

        # 4 entities: sanctioned company + CGU (item 1), sanctioned person + CGU (item 2)
        assert len(result.entities) == 4
        company = next(e for e in result.entities if e.type == "company")
        assert company.identifiers["cnpj"] == "12345678000199"
        person = next(e for e in result.entities if e.type == "person")
        assert person.identifiers["cpf"] == "21576805867"

    def test_normalize_servidores(self):
        items = [RawItem(raw_id="pt_srv:1:0", data={
            "id": 1234,
            "nome": "JOAO DA SILVA",
            "cpf": "***123456**",
            "orgaoServidorExercicio": "MEC",
            "cargoEfetivo": "ANALISTA",
            "remuneracaoBasicaBruta": "15000.00",
            "remuneracaoAposDeducoes": "12000.00",
            "mesAno": "202501",
        })]
        job = JobSpec(name="pt_servidores_remuneracao", description="", domain="remuneracao")
        result = self.c.normalize(job, items)
        # 2 entities: servant person + employer org (MEC)
        assert len(result.entities) == 2
        servant = next(e for e in result.entities if e.type == "person")
        assert servant.name == "JOAO DA SILVA"
        assert result.events[0].value_brl == 15000.0

    def test_normalize_viagens(self):
        items = [RawItem(raw_id="pt_viag:1:0", data={
            "id": 5, "nome": "MARIA", "cpf": "", "motivo": "Reunião",
            "valor": "2500.50", "destino": "Brasília", "orgao": "MF",
            "dataInicio": "2025-01-10", "dataFim": "2025-01-12",
        })]
        job = JobSpec(name="pt_viagens", description="", domain="despesa")
        result = self.c.normalize(job, items)
        assert result.events[0].type == "viagem"
        assert result.events[0].value_brl == 2500.50

    def test_normalize_cartao(self):
        items = [RawItem(raw_id="pt_cart:1:0", data={
            "id": 99, "portador": "CARLOS", "cpf": "",
            "unidadeGestora": {"nome": "PR"},
            "tipoCartao": "CPGF",
            "valorTransacao": "350.00",
            "estabelecimento": "Restaurante X",
            "dataTransacao": "2025-03-15",
        })]
        job = JobSpec(name="pt_cartao_pagamento", description="", domain="despesa")
        result = self.c.normalize(job, items)
        assert result.events[0].type == "pagamento_cartao"
        assert result.events[0].value_brl == 350.0

    def test_normalize_emendas(self):
        items = [RawItem(raw_id="pt_em:1:0", data={
            "codigoEmenda": 777, "autor": "DEP. FULANO",
            "tipoEmenda": "Individual", "localidadeGasto": "São Paulo",
            "valorEmpenhado": "1.489,00", "valorPago": "500.000,00",
            "ano": 2025, "funcao": "Saúde", "subfuncao": "Atenção Básica",
        })]
        job = JobSpec(name="pt_emendas", description="", domain="emenda")
        result = self.c.normalize(job, items)
        assert result.entities[0].name == "DEP. FULANO"
        assert result.events[0].type == "emenda"
        assert result.events[0].value_brl == 1489.0
        assert result.events[0].occurred_at == datetime(2025, 1, 1, tzinfo=timezone.utc)

    def test_normalize_convenios(self):
        items = [RawItem(raw_id="pt_conv:1:0", data={
            "id": 42, "proponente": "PREFEITURA X",
            "cnpjProponente": "99888777000100",
            "objeto": "Construção de UBS",
            "valorConvenio": "5000000.00",
            "numero": "123456", "orgaoConcedente": "MS", "situacao": "Em execução",
        })]
        job = JobSpec(name="pt_convenios_transferencias", description="", domain="transferencia")
        result = self.c.normalize(job, items)
        assert result.entities[0].type == "company"
        assert result.events[0].type == "convenio"
        assert result.events[0].value_brl == 5000000.0

    def test_normalize_generic_fallback(self):
        items = [RawItem(raw_id="pt_ben:1:0", data={"foo": "bar"})]
        job = JobSpec(name="pt_beneficios", description="", domain="beneficio")
        result = self.c.normalize(job, items)
        assert len(result.events) == 1
        assert result.events[0].type == "beneficio"

    def test_normalize_despesas_generic(self):
        items = [RawItem(raw_id="pt_desp:1:0", data={"valor": 100})]
        job = JobSpec(name="pt_despesas_execucao", description="", domain="despesa")
        result = self.c.normalize(job, items)
        assert result.events[0].type == "despesa"

    @pytest.mark.asyncio
    async def test_fetch_unknown_job_raises(self):
        job = JobSpec(name="pt_unknown", description="", domain="test")
        with pytest.raises(ValueError, match="Unknown job"):
            await self.c.fetch(job)

    @pytest.mark.asyncio
    async def test_fetch_despesas_windowed_range_uses_composite_cursor(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [{"id": 1}]
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "shared.connectors.portal_transparencia.portal_transparencia_client",
            return_value=mock_client,
        ):
            job = JobSpec(name="pt_despesas_execucao", description="", domain="despesa")
            items, next_cursor = await self.c.fetch(
                job,
                params={"mesAnoInicio": "03/2023", "mesAnoFim": "02/2026"},
            )

            assert len(items) == 1
            assert next_cursor == "w0p2"
            called_params = mock_client.get.call_args.kwargs["params"]
            assert called_params["pagina"] == 1
            assert called_params["mesAnoInicio"] == "03/2023"
            assert called_params["mesAnoFim"] == "02/2024"
            assert items[0].raw_id.startswith("pt_despesas_execucao:w0p1:")

    @pytest.mark.asyncio
    async def test_fetch_list_response(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [
            {"id": 1, "nome": "Test"}, {"id": 2, "nome": "Test2"},
        ]
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("shared.connectors.portal_transparencia.portal_transparencia_client", return_value=mock_client):
            job = self.c.list_jobs()[0]
            items, next_cursor = await self.c.fetch(job)
            assert len(items) == 2
            assert items[0].data["id"] == 1
            assert next_cursor == "2"  # 2 items returned → more pages may exist

    @pytest.mark.asyncio
    async def test_fetch_with_cursor(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [{"id": i} for i in range(100)]
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("shared.connectors.portal_transparencia.portal_transparencia_client", return_value=mock_client):
            job = self.c.list_jobs()[0]
            items, next_cursor = await self.c.fetch(job, cursor="2")
            assert len(items) == 100
            assert next_cursor == "3"

    @pytest.mark.asyncio
    async def test_fetch_dict_wrapper_response(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"data": [{"id": 1}]}
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("shared.connectors.portal_transparencia.portal_transparencia_client", return_value=mock_client):
            job = self.c.list_jobs()[0]
            items, next_cursor = await self.c.fetch(job, params={"ano": 2025})
            assert len(items) == 1

    def test_safe_float_none(self):
        from shared.connectors.portal_transparencia import _safe_float
        assert _safe_float(None) is None
        assert _safe_float("not_a_number") is None
        assert _safe_float(42) == 42.0
        assert _safe_float("3.14") == 3.14
        assert _safe_float("1.489,00") == 1489.0

    def test_parse_dimension_cursor(self):
        from shared.connectors.portal_transparencia import _parse_dimension_cursor
        assert _parse_dimension_cursor("d42w3p7") == (42, 3, 7)
        assert _parse_dimension_cursor("d0w0p1") == (0, 0, 1)
        assert _parse_dimension_cursor(None) == (0, 0, 1)
        assert _parse_dimension_cursor("") == (0, 0, 1)
        assert _parse_dimension_cursor("w3p2") == (0, 0, 1)  # Legacy cursor
        assert _parse_dimension_cursor("d100w55p999") == (100, 55, 999)

    @pytest.mark.asyncio
    async def test_fetch_dimension_windowed_servidores(self):
        """Dimension-keyed fetch for servidores iterates per SIAPE organ."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [{"id": 1, "nome": "JOAO", "mesAno": "202501"}]
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "shared.connectors.portal_transparencia.portal_transparencia_client",
            return_value=mock_client,
        ), patch.object(
            self.c, "_get_dimension_keys", return_value=["26000", "26100"]
        ):
            job = JobSpec(name="pt_servidores_remuneracao", description="", domain="remuneracao")
            items, next_cursor = await self.c.fetch(job)

            assert len(items) == 1
            assert items[0].raw_id.startswith("pt_servidores_remuneracao:d0w0p1:")
            # 1 item < 100 → advance to next window
            assert next_cursor is not None
            # Verify the organ code was sent
            called_params = mock_client.get.call_args.kwargs["params"]
            assert called_params["orgaoServidorExercicio"] == "26000"

    @pytest.mark.asyncio
    async def test_fetch_dimension_windowed_beneficios(self):
        """Dimension-keyed fetch for beneficios iterates per IBGE municipality."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [{"id": 1, "valor": "500.00", "mesAno": "202501"}]
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "shared.connectors.portal_transparencia.portal_transparencia_client",
            return_value=mock_client,
        ), patch.object(
            self.c, "_get_dimension_keys", return_value=["3550308"]
        ):
            job = JobSpec(name="pt_beneficios", description="", domain="beneficio")
            items, next_cursor = await self.c.fetch(job)

            assert len(items) == 1
            called_params = mock_client.get.call_args.kwargs["params"]
            assert called_params["codigoIbge"] == "3550308"

    @pytest.mark.asyncio
    async def test_fetch_dimension_windowed_exhausted_dimensions(self):
        """When all dimensions are exhausted, cursor is None."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = []  # no data
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "shared.connectors.portal_transparencia.portal_transparencia_client",
            return_value=mock_client,
        ), patch.object(
            self.c, "_get_dimension_keys", return_value=["26000"]
        ):
            job = JobSpec(name="pt_servidores_remuneracao", description="", domain="remuneracao")
            # Start beyond the only dimension key
            items, next_cursor = await self.c.fetch(job, cursor="d1w0p1")
            assert items == []
            assert next_cursor is None

    @pytest.mark.asyncio
    async def test_fetch_dimension_windowed_400_skips_to_valid_dimension(self):
        """A 400 error on dim 0 skips forward until finding valid data."""
        bad_resp = MagicMock()
        bad_resp.status_code = 400
        bad_resp.raise_for_status = MagicMock(side_effect=httpx.HTTPStatusError(
            "Bad Request", request=MagicMock(), response=bad_resp
        ))

        good_resp = MagicMock()
        good_resp.status_code = 200
        good_resp.json.return_value = [{"id": 1, "nome": "SERVIDOR"}]
        good_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        # First call (dim 0) → 400, second call (dim 1) → 200 with data
        mock_client.get.side_effect = [bad_resp, good_resp]
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "shared.connectors.portal_transparencia.portal_transparencia_client",
            return_value=mock_client,
        ), patch.object(
            self.c, "_get_dimension_keys", return_value=["99999", "26000"]
        ):
            job = JobSpec(name="pt_servidores_remuneracao", description="", domain="remuneracao")
            items, next_cursor = await self.c.fetch(job, cursor="d0w0p1")
            assert len(items) == 1
            # Verify the item's raw_id shows it landed on dim 1
            assert "d1w0p1" in items[0].raw_id


# ── Câmara ──────────────────────────────────────────────────────────

class TestCamara:
    def setup_method(self):
        self.c = get_connector("camara")

    def test_name(self):
        assert self.c.name == "camara"

    def test_has_3_jobs(self):
        assert len(self.c.list_jobs()) == 3

    def test_normalize_deputados(self):
        items = [RawItem(raw_id="dep:1:0", data={
            "id": 204521, "nome": "FULANO DE TAL",
            "siglaPartido": "PT", "siglaUf": "SP",
            "urlFoto": "https://foto.jpg", "email": "dep@camara.leg.br",
        })]
        job = JobSpec(name="camara_deputados", description="", domain="legislativo")
        result = self.c.normalize(job, items)
        assert len(result.entities) == 1
        assert result.entities[0].name == "FULANO DE TAL"
        assert result.entities[0].attrs["sigla_partido"] == "PT"

    def test_normalize_despesas(self):
        items = [RawItem(raw_id="desp:1:0", data={
            "tipoDespesa": "PASSAGEM AÉREA", "valorDocumento": 3500.0,
            "ano": 2025, "mes": 3, "nomeFornecedor": "GOL",
            "cnpjCpfFornecedor": "07868015000160", "valorLiquido": 3400.0,
        })]
        job = JobSpec(name="camara_despesas_cota", description="", domain="despesa")
        result = self.c.normalize(job, items)
        assert result.events[0].type == "despesa_cota"
        assert result.events[0].value_brl == 3500.0

    def test_normalize_orgaos(self):
        items = [RawItem(raw_id="org:1:0", data={
            "id": 123, "nome": "Comissão de Educação",
            "sigla": "CE", "tipoOrgao": "Comissão",
        })]
        job = JobSpec(name="camara_orgaos", description="", domain="legislativo")
        result = self.c.normalize(job, items)
        assert result.entities[0].type == "org"
        assert result.entities[0].attrs["sigla"] == "CE"

    def test_normalize_unknown_job(self):
        job = JobSpec(name="camara_unknown", description="", domain="test")
        result = self.c.normalize(job, [])
        assert len(result.entities) == 0
        assert len(result.events) == 0

    @pytest.mark.asyncio
    async def test_fetch_deputados(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"dados": [{"id": 1, "nome": "Test"}]}
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("shared.connectors.camara.camara_client", return_value=mock_client):
            job = JobSpec(name="camara_deputados", description="", domain="legislativo")
            items, cursor = await self.c.fetch(job)
            assert len(items) == 1

    @pytest.mark.asyncio
    async def test_fetch_despesas_auto_discover(self):
        """Without deputado_id, auto-fetches deputies then their expenses."""
        mock_dep_resp = MagicMock()
        mock_dep_resp.json.return_value = {"dados": [{"id": 204521, "nome": "DEP A"}]}
        mock_dep_resp.raise_for_status = MagicMock()

        mock_exp_resp = MagicMock()
        mock_exp_resp.json.return_value = {"dados": [{"tipoDespesa": "PASSAGEM", "valorDocumento": 100}]}
        mock_exp_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.side_effect = [mock_dep_resp, mock_exp_resp]
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("shared.connectors.camara.camara_client", return_value=mock_client):
            job = JobSpec(name="camara_despesas_cota", description="", domain="despesa")
            items, cursor = await self.c.fetch(job)
            assert len(items) == 1
            # 1 deputy (less than full page) → advance to next year's deputies
            assert cursor == "y1d1:0"

    @pytest.mark.asyncio
    async def test_fetch_despesas_with_params(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"dados": [{"val": 100}]}
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("shared.connectors.camara.camara_client", return_value=mock_client):
            job = JobSpec(name="camara_despesas_cota", description="", domain="despesa")
            items, _ = await self.c.fetch(job, params={"deputado_id": "204521", "ano": 2025})
            assert len(items) == 1

    @pytest.mark.asyncio
    async def test_fetch_orgaos(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"dados": [{"id": 1, "nome": "CE"}]}
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("shared.connectors.camara.camara_client", return_value=mock_client):
            job = JobSpec(name="camara_orgaos", description="", domain="legislativo")
            items, _ = await self.c.fetch(job)
            assert len(items) == 1

    @pytest.mark.asyncio
    async def test_fetch_unknown_job_raises(self):
        job = JobSpec(name="camara_invalid", description="", domain="test")
        with pytest.raises(ValueError, match="Unknown job"):
            await self.c.fetch(job)


# ── Senado ──────────────────────────────────────────────────────────

class TestSenado:
    def setup_method(self):
        self.c = get_connector("senado")

    def test_name(self):
        assert self.c.name == "senado"

    def test_has_2_jobs(self):
        assert len(self.c.list_jobs()) == 2
        jobs = {j.name: j for j in self.c.list_jobs()}
        assert jobs["senado_ceaps"].enabled is True

    def test_normalize_senadores(self):
        items = [RawItem(raw_id="sen:0", data={
            "IdentificacaoParlamentar": {
                "CodigoParlamentar": "5012",
                "NomeParlamentar": "SENADOR TESTE",
                "SiglaPartidoParlamentar": "MDB",
                "UfParlamentar": "RJ",
                "UrlFotoParlamentar": "https://foto.jpg",
            }
        })]
        job = JobSpec(name="senado_senadores", description="", domain="legislativo")
        result = self.c.normalize(job, items)
        assert len(result.entities) == 1
        assert result.entities[0].name == "SENADOR TESTE"
        assert result.entities[0].identifiers["codigo_parlamentar"] == "5012"

    def test_normalize_ceaps(self):
        items = [RawItem(raw_id="ceaps:5012:2025:0", data={
            "_senator_codigo": "5012",
            "NomeParlamentar": "SEN TESTE",
            "Data": "2025-02-07",
            "ValorReembolsado": "1000.00",
            "TipoDespesa": "Divulgação da atividade parlamentar",
            "Detalhamento": "Serviço de comunicação",
            "Fornecedor": "EMPRESA MIDIA LTDA",
            "CNPJCPF": "12345678000199",
            "NumeroDocumento": "2088478",
        })]
        job = JobSpec(name="senado_ceaps", description="", domain="despesa")
        result = self.c.normalize(job, items)
        assert len(result.entities) == 2  # senator + supplier
        assert result.entities[0].name == "SEN TESTE"
        assert result.events[0].type == "despesa"
        assert result.events[0].subtype == "ceaps"
        assert result.events[0].value_brl == 1000.0
        assert result.events[0].occurred_at == datetime(2025, 2, 7, tzinfo=timezone.utc)
        roles = sorted(p.role for p in result.events[0].participants)
        assert "buyer" in roles
        assert "supplier" in roles

    def test_normalize_unknown_returns_empty(self):
        job = JobSpec(name="senado_unknown", description="", domain="test")
        result = self.c.normalize(job, [])
        assert len(result.entities) == 0

    @pytest.mark.asyncio
    async def test_fetch_senadores(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "ListaParlamentarEmExercicio": {
                "Parlamentares": {
                    "Parlamentar": [
                        {"IdentificacaoParlamentar": {"NomeParlamentar": "SEN A"}},
                        {"IdentificacaoParlamentar": {"NomeParlamentar": "SEN B"}},
                    ]
                }
            }
        }
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("shared.connectors.senado.senado_client", return_value=mock_client):
            job = JobSpec(name="senado_senadores", description="", domain="legislativo")
            items, cursor = await self.c.fetch(job)
            assert len(items) == 2
            assert cursor is None

    @pytest.mark.asyncio
    async def test_fetch_senadores_single_dict(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "ListaParlamentarEmExercicio": {
                "Parlamentares": {
                    "Parlamentar": {"IdentificacaoParlamentar": {"NomeParlamentar": "SEN A"}},
                }
            }
        }
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("shared.connectors.senado.senado_client", return_value=mock_client):
            job = JobSpec(name="senado_senadores", description="", domain="legislativo")
            items, _ = await self.c.fetch(job)
            assert len(items) == 1

    @pytest.mark.asyncio
    async def test_fetch_ceaps(self):
        # Mock _get_senator_codes to return a single senator
        ceaps_resp = MagicMock()
        ceaps_resp.status_code = 200
        ceaps_resp.headers = {"content-type": "application/json"}
        ceaps_resp.json.return_value = {
            "CesapAtual": {
                "Despesas": {
                    "Despesa": [
                        {"Data": "2025-01-10", "ValorReembolsado": "500", "Fornecedor": "A"},
                        {"Data": "2025-01-11", "ValorReembolsado": "300", "Fornecedor": "B"},
                    ]
                }
            }
        }
        ceaps_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = ceaps_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("shared.connectors.senado.senado_client", return_value=mock_client),
            patch.object(self.c, "_get_senator_codes", return_value=["5012"]),
        ):
            job = JobSpec(name="senado_ceaps", description="", domain="despesa")
            items, cursor = await self.c.fetch(job, params={"ano": "2025"})
            assert len(items) == 2
            assert cursor is None  # single senator, single year

    @pytest.mark.asyncio
    async def test_fetch_ceaps_iterates_senators(self):
        ceaps_resp = MagicMock()
        ceaps_resp.status_code = 200
        ceaps_resp.headers = {"content-type": "application/json"}
        ceaps_resp.json.return_value = {
            "CesapAtual": {"Despesas": {"Despesa": [{"Data": "2025-01-10"}]}}
        }
        ceaps_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = ceaps_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("shared.connectors.senado.senado_client", return_value=mock_client),
            patch.object(self.c, "_get_senator_codes", return_value=["5012", "5013"]),
        ):
            job = JobSpec(name="senado_ceaps", description="", domain="despesa")
            # First call: senator 0, year 0 → cursor advances to senator 1
            items, cursor = await self.c.fetch(job, params={"ano": "2025"})
            assert len(items) == 1
            assert cursor == "s1y0"

    @pytest.mark.asyncio
    async def test_fetch_unknown_raises(self):
        job = JobSpec(name="senado_unknown", description="", domain="test")
        with pytest.raises(ValueError, match="Unknown job"):
            await self.c.fetch(job)


# ── Compras Gov ─────────────────────────────────────────────────────

class TestComprasGov:
    def setup_method(self):
        self.c = get_connector("compras_gov")

    def test_name(self):
        assert self.c.name == "compras_gov"

    def test_has_3_jobs(self):
        assert len(self.c.list_jobs()) == 3
        jobs = {j.name: j for j in self.c.list_jobs()}
        assert jobs["compras_licitacoes_by_period"].enabled is True

    def test_rate_limit(self):
        assert self.c.rate_limit_policy().requests_per_second == 10

    def test_normalize_licitacoes(self):
        items = [RawItem(raw_id="lic:1:0", data={
            "uasg": 170001, "nomeUasg": "MINISTERIO DA FAZENDA",
            "modalidade": "Pregão", "objeto": "Aquisição de TI",
            "valorEstimado": 500000.0, "numero": "01/2025", "situacao": "Aberta",
            "dataPublicacaoPncp": "2025-01-10",
        })]
        job = JobSpec(name="compras_licitacoes_by_period", description="", domain="licitacao")
        result = self.c.normalize(job, items)
        assert len(result.entities) == 1
        assert result.entities[0].type == "org"
        assert result.events[0].type == "licitacao"
        assert result.events[0].value_brl == 500000.0
        assert result.events[0].occurred_at == datetime(2025, 1, 10, tzinfo=timezone.utc)
        assert result.events[0].attrs["modality"] == "Pregão"
        roles = sorted(p.role for p in result.events[0].participants)
        assert "buyer" in roles
        assert "procuring_entity" in roles

    def test_normalize_licitacoes_extracts_winner_and_bidders(self):
        items = [RawItem(raw_id="lic:1:1", data={
            "uasg": 170001,
            "nomeUasg": "MINISTERIO DA FAZENDA",
            "modalidade": "Pregão",
            "objeto": "Aquisição de TI",
            "valorEstimado": 500000.0,
            "vencedor": {
                "nome": "EMPRESA VENCEDORA LTDA",
                "cnpj": "12.345.678/0001-99",
            },
            "participantes": [
                {"nome": "EMPRESA VENCEDORA LTDA", "cnpj": "12.345.678/0001-99"},
                {"nome": "EMPRESA BIDDER SA", "cnpj": "98.765.432/0001-10"},
            ],
        })]
        job = JobSpec(name="compras_licitacoes_by_period", description="", domain="licitacao")
        result = self.c.normalize(job, items)

        roles = [p.role for p in result.events[0].participants]
        assert "winner" in roles
        assert "bidder" in roles

    def test_normalize_generic(self):
        items = [RawItem(raw_id="cat:1:0", data={"id": 1})]
        job = JobSpec(name="compras_catalogo_catmat_full", description="", domain="catalogo")
        result = self.c.normalize(job, items)
        assert result.events[0].type == "catalogo"

    @pytest.mark.asyncio
    async def test_fetch(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [{"id": 1}]
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("shared.connectors.compras_gov.compras_gov_client", return_value=mock_client):
            job = self.c.list_jobs()[0]
            items, _ = await self.c.fetch(job)
            assert len(items) == 1

    @pytest.mark.asyncio
    async def test_fetch_with_params(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [{"id": 1}]
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("shared.connectors.compras_gov.compras_gov_client", return_value=mock_client):
            job = self.c.list_jobs()[0]
            items, _ = await self.c.fetch(job, params={"ano": 2025})
            assert len(items) == 1

    @pytest.mark.asyncio
    async def test_fetch_embedded_response(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"_embedded": {"registros": [{"id": 1}, {"id": 2}]}}
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("shared.connectors.compras_gov.compras_gov_client", return_value=mock_client):
            job = self.c.list_jobs()[0]
            items, _ = await self.c.fetch(job)
            assert len(items) == 2

    @pytest.mark.asyncio
    async def test_fetch_licitacoes_falls_back_to_pncp_on_timeout(self):
        primary_client = AsyncMock()
        primary_client.get.side_effect = httpx.ReadTimeout("timed out")
        primary_client.__aenter__ = AsyncMock(return_value=primary_client)
        primary_client.__aexit__ = AsyncMock(return_value=False)

        fallback_resp = MagicMock()
        fallback_resp.raise_for_status = MagicMock()
        fallback_resp.json.return_value = {
            "data": [
                {
                    "numeroControlePNCP": "pncp-licitacao-1",
                    "numeroCompra": "90001/2026",
                    "modalidadeNome": "Pregao",
                    "objetoCompra": "Aquisição de equipamentos",
                    "valorTotalEstimado": 12345.67,
                    "situacaoCompra": "PUBLICADO",
                    "orgaoEntidade": {"razaoSocial": "MINISTERIO TESTE"},
                    "unidadeOrgao": {"codigoUnidade": "170001", "nomeUnidade": "UASG TESTE"},
                }
            ]
        }

        fallback_client = AsyncMock()
        fallback_client.get.return_value = fallback_resp
        fallback_client.__aenter__ = AsyncMock(return_value=fallback_client)
        fallback_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("shared.connectors.compras_gov.compras_gov_client", return_value=primary_client),
            patch("shared.connectors.compras_gov.pncp_client", return_value=fallback_client),
        ):
            job = JobSpec(name="compras_licitacoes_by_period", description="", domain="licitacao")
            items, _ = await self.c.fetch(job)

            assert len(items) == 1
            assert items[0].data["source_fallback"] == "pncp"
            assert items[0].data["modalidade"] == "Pregao"

    @pytest.mark.asyncio
    async def test_fetch_licitacoes_fallback_sets_required_modalidade_param(self):
        primary_client = AsyncMock()
        primary_client.get.side_effect = httpx.ReadTimeout("timed out")
        primary_client.__aenter__ = AsyncMock(return_value=primary_client)
        primary_client.__aexit__ = AsyncMock(return_value=False)

        fallback_resp = MagicMock()
        fallback_resp.raise_for_status = MagicMock()
        fallback_resp.json.return_value = {"data": []}

        fallback_client = AsyncMock()
        fallback_client.get.return_value = fallback_resp
        fallback_client.__aenter__ = AsyncMock(return_value=fallback_client)
        fallback_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("shared.connectors.compras_gov.compras_gov_client", return_value=primary_client),
            patch("shared.connectors.compras_gov.pncp_client", return_value=fallback_client),
        ):
            job = JobSpec(name="compras_licitacoes_by_period", description="", domain="licitacao")
            await self.c.fetch(job)

            assert fallback_client.get.called
            params = fallback_client.get.call_args.kwargs["params"]
            assert "codigoModalidadeContratacao" in params

    @pytest.mark.asyncio
    async def test_fetch_unknown_endpoint_raises(self):
        job = JobSpec(name="compras_unknown", description="", domain="test")
        with pytest.raises(ValueError, match="Unknown job"):
            await self.c.fetch(job)


# ── ComprasNet Contratos ────────────────────────────────────────────

class TestComprasNetContratos:
    def setup_method(self):
        self.c = get_connector("comprasnet_contratos")

    def test_name(self):
        assert self.c.name == "comprasnet_contratos"

    def test_has_1_job(self):
        assert len(self.c.list_jobs()) == 1

    def test_job_is_enabled(self):
        assert self.c.list_jobs()[0].enabled is True

    def test_rate_limit(self):
        assert self.c.rate_limit_policy().requests_per_second == 5

    def test_normalize(self):
        items = [RawItem(raw_id="cn:0:0", data={
            "fornecedor_cnpj_cpf_idgener": "11222333000144",
            "fornecedor_nome": "EMPRESA ABC",
            "objeto": "Limpeza predial",
            "valor_global": 1200000.0,
            "numero": "001/2025", "categoria": "Vigente",
            "data_assinatura": "2025-01-01", "vigencia_fim": "2026-01-01",
            "orgao_nome": "MIN FAZENDA", "unidade_codigo": "170001",
        })]
        job = self.c.list_jobs()[0]
        result = self.c.normalize(job, items)
        assert result.entities[0].identifiers["cnpj"] == "11222333000144"
        assert result.events[0].type == "contrato"
        roles = sorted(p.role for p in result.events[0].participants)
        assert "supplier" in roles
        assert "buyer" in roles
        assert "procuring_entity" in roles
        assert result.events[0].occurred_at is not None
        assert result.events[0].attrs["contract_start"] is not None

    @pytest.mark.asyncio
    async def test_fetch_contracts(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [{"id": 1}]
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("shared.connectors.comprasnet_contratos.comprasnet_contratos_client", return_value=mock_client):
            job = self.c.list_jobs()[0]  # cnet_contracts
            items, _ = await self.c.fetch(job)
            assert len(items) == 1

    @pytest.mark.asyncio
    async def test_fetch_contracts_falls_back_to_pncp_on_timeout(self):
        primary_client = AsyncMock()
        primary_client.get.side_effect = httpx.ReadTimeout("timed out")
        primary_client.__aenter__ = AsyncMock(return_value=primary_client)
        primary_client.__aexit__ = AsyncMock(return_value=False)

        fallback_resp = MagicMock()
        fallback_resp.raise_for_status = MagicMock()
        fallback_resp.json.return_value = {
            "data": [
                {
                    "niFornecedor": "11222333000144",
                    "nomeRazaoSocialFornecedor": "FORNECEDOR TESTE",
                    "objetoContrato": "Servico de TI",
                    "valorGlobal": 1500.0,
                    "numeroContratoEmpenho": "CT-01",
                    "dataAssinatura": "2026-01-02",
                    "dataVigenciaInicio": "2026-01-02",
                    "dataVigenciaFim": "2026-12-31",
                    "orgaoEntidade": {"razaoSocial": "ORGAO XYZ"},
                    "unidadeOrgao": {"codigoUnidade": "170001"},
                    "categoriaProcesso": {"descricao": "Pregao"},
                    "numeroControlePNCP": "170001-1-000001/2026",
                }
            ]
        }

        fallback_client = AsyncMock()
        fallback_client.get.return_value = fallback_resp
        fallback_client.__aenter__ = AsyncMock(return_value=fallback_client)
        fallback_client.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "shared.connectors.comprasnet_contratos.comprasnet_contratos_client",
            return_value=primary_client,
        ), patch(
            "shared.connectors.comprasnet_contratos.pncp_client",
            return_value=fallback_client,
        ):
            job = self.c.list_jobs()[0]
            items, _ = await self.c.fetch(job)

        assert len(items) == 1
        payload = items[0].data
        assert payload["source_fallback"] == "pncp"
        assert payload["fornecedor_cnpj_cpf_idgener"] == "11222333000144"


# ── PNCP ────────────────────────────────────────────────────────────

class TestPNCP:
    def setup_method(self):
        self.c = get_connector("pncp")

    def test_name(self):
        assert self.c.name == "pncp"

    def test_has_3_jobs(self):
        assert len(self.c.list_jobs()) == 3

    def test_rate_limit(self):
        assert self.c.rate_limit_policy().requests_per_second == 10

    def test_normalize(self):
        items = [RawItem(raw_id="pncp:1:0", data={
            "cnpjOrgao": "00394445000166", "nomeOrgao": "UFMG",
            "objetoCompra": "Material didático", "valorTotalEstimado": 80000.0,
            "modalidadeNome": "Pregão Eletrônico", "situacaoCompra": "Publicado",
        })]
        job = self.c.list_jobs()[0]
        result = self.c.normalize(job, items)
        assert result.entities[0].name == "UFMG"
        assert result.events[0].value_brl == 80000.0
        assert "source_limitations" in result.events[0].attrs

    def test_normalize_enriches_limitation_sensitive_attrs(self):
        items = [RawItem(raw_id="pncp:1:1", data={
            "cnpjOrgao": "00394445000166",
            "nomeOrgao": "UFMG",
            "objetoCompra": "Obra teste",
            "valorTotalEstimado": 120000.0,
            "modalidadeNome": "Inexigibilidade",
            "situacaoCompra": "Publicado",
            "beneficioMicroEmpresa": "true",
            "tipoInexigibilidade": "fornecedor exclusivo",
            "pmiRealizado": "sim",
            "porteFornecedor": "ME",
        })]
        job = self.c.list_jobs()[0]
        result = self.c.normalize(job, items)
        attrs = result.events[0].attrs
        assert attrs["me_epp_exclusive"] is True
        assert attrs["inexigibilidade_subtype"] == "fornecedor exclusivo"
        assert attrs["pmi_realizado"] is True
        assert attrs["porte_empresa"] == "ME"
        assert "source_limitations" not in attrs

    @pytest.mark.asyncio
    async def test_fetch(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [{"id": 1}]
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("shared.connectors.pncp.pncp_client", return_value=mock_client):
            job = self.c.list_jobs()[0]
            items, _ = await self.c.fetch(job)
            assert len(items) == 1

    @pytest.mark.asyncio
    async def test_fetch_with_params(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [{"id": 1}]
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("shared.connectors.pncp.pncp_client", return_value=mock_client):
            job = self.c.list_jobs()[0]
            items, _ = await self.c.fetch(job, params={"dataInicio": "2025-01-01"})
            assert len(items) == 1

    @pytest.mark.asyncio
    async def test_fetch_unknown_endpoint_raises(self):
        job = JobSpec(name="pncp_unknown", description="", domain="test")
        with pytest.raises(ValueError, match="Unknown job"):
            await self.c.fetch(job)


# ── TransfereGov ────────────────────────────────────────────────────

class TestTransfereGov:
    def setup_method(self):
        self.c = get_connector("transferegov")

    def test_name(self):
        assert self.c.name == "transferegov"

    def test_has_2_jobs(self):
        assert len(self.c.list_jobs()) == 2

    def test_default_rate_limit(self):
        assert self.c.rate_limit_policy().requests_per_second == 5

    def test_normalize_transferencias_especiais(self):
        items = [RawItem(raw_id="tg:0:0", data={
            "id_plano_acao": 3221,
            "ano_plano_acao": 2021,
            "codigo_plano_acao": "0903-003221",
            "situacao_plano_acao": "CIENTE",
            "cnpj_beneficiario_plano_acao": "04218211000156",
            "nome_beneficiario_plano_acao": "MUNICIPIO DE PAU D:ARCO DO PIAUI",
            "uf_beneficiario_plano_acao": "PI",
            "nome_parlamentar_emenda_plano_acao": "Iracema Portella",
            "valor_custeio_plano_acao": 30000.0,
            "valor_investimento_plano_acao": 80000.0,
        })]
        job = next(j for j in self.c.list_jobs() if j.name == "transferegov_transferencias_especiais")
        result = self.c.normalize(job, items)
        assert result.entities[0].name == "MUNICIPIO DE PAU D:ARCO DO PIAUI"
        assert result.events[0].type == "transferencia"
        assert result.events[0].value_brl == 110000.0
        assert result.events[0].occurred_at == datetime(2021, 1, 1, tzinfo=timezone.utc)
        assert result.events[0].participants[0].role == "beneficiario"

    def test_normalize_ted(self):
        items = [RawItem(raw_id="ted:0:0", data={
            "id_termo": 9,
            "id_plano_acao": 19,
            "tx_situacao_termo": "CUMPRIMENTO_OBJETO_INICIADO",
            "tx_numero_ns_termo": "2022NS000303",
            "dt_assinatura_termo": "2024-05-17",
        })]
        job = next(j for j in self.c.list_jobs() if j.name == "transferegov_ted")
        result = self.c.normalize(job, items)
        assert result.entities[0].source_id == "plano_acao:19"
        assert result.events[0].type == "transferencia"
        assert result.events[0].occurred_at == datetime(2024, 5, 17, tzinfo=timezone.utc)
        assert result.events[0].attrs["id_termo"] == 9

    @pytest.mark.asyncio
    async def test_fetch(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [{"id": 1}]
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("shared.connectors.transferegov.transferegov_client", return_value=mock_client):
            job = next(j for j in self.c.list_jobs() if j.name == "transferegov_ted")
            items, _ = await self.c.fetch(job)
            assert len(items) == 1
            mock_client.get.assert_called_once()
            called_endpoint = mock_client.get.call_args.args[0]
            assert called_endpoint == "/termo_execucao"

    @pytest.mark.asyncio
    async def test_fetch_transferencias_especiais_uses_plano_acao_endpoint(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [{"id": 1}]
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("shared.connectors.transferegov.transferegov_client", return_value=mock_client):
            job = next(j for j in self.c.list_jobs() if j.name == "transferegov_transferencias_especiais")
            items, _ = await self.c.fetch(job)
            assert len(items) == 1
            mock_client.get.assert_called_once()
            called_endpoint = mock_client.get.call_args.args[0]
            assert called_endpoint == "/plano_acao_especial"

    @pytest.mark.asyncio
    async def test_fetch_unknown_endpoint_raises(self):
        job = JobSpec(name="transferegov_unknown", description="", domain="test")
        with pytest.raises(ValueError, match="Unknown job"):
            await self.c.fetch(job)


# ── TSE ─────────────────────────────────────────────────────────────

class TestTSE:
    def setup_method(self):
        self.c = get_connector("tse")

    def test_name(self):
        assert self.c.name == "tse"

    def test_has_4_jobs(self):
        jobs = {j.name for j in self.c.list_jobs()}
        assert jobs == {
            "tse_candidatos",
            "tse_bens_candidatos",
            "tse_receitas_candidatos",
            "tse_doacoes",
            "tse_despesas_candidatos",
        }

    def test_normalize_bens(self):
        items = [RawItem(raw_id="tse:1:0", data={
            "SQ_CANDIDATO": "12345", "NM_CANDIDATO": "CANDIDATO X",
            "NR_CPF_CANDIDATO": "99988877766",
            "DS_BEM_CANDIDATO": "Casa", "VR_BEM_CANDIDATO": "500000.00",
            "ANO_ELEICAO": "2024", "DS_CARGO": "Deputado Federal",
            "SG_PARTIDO": "PL",
        })]
        job = JobSpec(name="tse_bens_candidatos", description="", domain="patrimonio")
        result = self.c.normalize(job, items)
        assert len(result.entities) == 1
        assert result.entities[0].name == "CANDIDATO X"
        assert result.events[0].value_brl == 500000.0

    def test_normalize_receitas_adds_portuguese_and_english_roles(self):
        items = [RawItem(raw_id="tse:receita:0", data={
            "SQ_CANDIDATO": "12345",
            "NM_CANDIDATO": "CANDIDATO X",
            "NM_DOADOR": "EMPRESA Y",
            "NR_CPF_CNPJ_DOADOR": "12345678000199",
            "VR_RECEITA": "10000.00",
            "DS_ORIGEM_RECEITA": "Doacao",
            "SG_UF": "DF",
            "ANO_ELEICAO": "2024",
            "DT_RECEITA": "2024-10-01",
        })]
        job = JobSpec(name="tse_receitas_candidatos", description="", domain="doacao_eleitoral")
        result = self.c.normalize(job, items)
        roles = sorted(p.role for p in result.events[0].participants)
        assert "doador" in roles
        assert "donor" in roles
        assert "candidato" in roles
        assert "recipient" in roles


# ── Regression: Senado log NameError ────────────────────────────────
# Bug: _fetch_ceaps used `log.warning(...)` but `log` was not imported,
# causing NameError on every 404 response from the senator CEAPS endpoint.

class TestSenadoCeaps404Regression:
    """Regression tests for NameError in _fetch_ceaps and 404/204 handling."""

    def test_senado_module_has_log_import(self):
        """log must be importable at module level — prevents NameError regression."""
        import shared.connectors.senado as senado_mod
        assert hasattr(senado_mod, "log"), (
            "shared.connectors.senado missing 'log' — _fetch_ceaps will crash on 404"
        )

    @pytest.mark.asyncio
    async def test_fetch_ceaps_404_returns_empty_and_advances_cursor(self):
        """404 from senator CEAPS endpoint must NOT raise — return ([], next_cursor)."""
        c = get_connector("senado")

        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch.object(c, "_get_senator_codes", return_value=["5012", "5013"]),
            patch("shared.connectors.senado.senado_client", return_value=mock_client),
        ):
            items, next_cursor = await c._fetch_ceaps(cursor=None, params=None)

        assert items == []
        # Must advance to the next entry rather than stalling
        assert next_cursor is not None

    @pytest.mark.asyncio
    async def test_fetch_ceaps_204_returns_empty_and_advances_cursor(self):
        """204 from senator CEAPS endpoint must NOT raise — return ([], next_cursor)."""
        c = get_connector("senado")

        mock_resp = MagicMock()
        mock_resp.status_code = 204
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch.object(c, "_get_senator_codes", return_value=["5012", "5013"]),
            patch("shared.connectors.senado.senado_client", return_value=mock_client),
        ):
            items, next_cursor = await c._fetch_ceaps(cursor=None, params=None)

        assert items == []
        assert next_cursor is not None

    @pytest.mark.asyncio
    async def test_fetch_ceaps_no_senator_codes_returns_empty(self):
        """Empty senator list must return ([], None) without HTTP calls."""
        c = get_connector("senado")
        with patch.object(c, "_get_senator_codes", return_value=[]):
            items, next_cursor = await c._fetch_ceaps(cursor=None, params=None)
        assert items == []
        assert next_cursor is None


# ── Regression: TSE BadZipFile ───────────────────────────────────────
# Bug: TSE CDN sometimes returns an HTML error page with HTTP 200 instead
# of a real ZIP. zipfile.ZipFile() then raised BadZipFile. The fix validates
# with zipfile.is_zipfile() before extraction, deletes the corrupt file, and
# raises FileNotFoundError so the next Celery retry downloads fresh.

class TestTSECorruptZipRegression:
    """Regression tests for BadZipFile when TSE CDN returns non-ZIP content."""

    @pytest.mark.asyncio
    async def test_corrupt_zip_raises_file_not_found_and_deletes_file(self, tmp_path):
        """A downloaded file that is not a valid ZIP must be deleted and raise FileNotFoundError."""
        import os
        from shared.connectors.tse import _TSEJobCfg, _download_tse_dataset

        cfg = _TSEJobCfg(
            zip_dir="prestacao_contas",
            zip_prefix="prestacao_de_contas_eleitorais_candidatos",
            csv_prefix="despesas_contratadas_candidatos",
        )
        year = 2024
        zip_filename = f"{cfg.zip_prefix}_{year}.zip"
        zip_path = tmp_path / zip_filename
        # Simulate CDN returning an HTML error page saved as a ZIP
        zip_path.write_bytes(b"<html><body>Service Unavailable</body></html>")

        assert zip_path.exists()

        with pytest.raises(FileNotFoundError, match="not a valid ZIP"):
            await _download_tse_dataset(cfg, year, str(tmp_path))

        # Corrupt file must be deleted so the next run re-downloads
        assert not zip_path.exists(), "Corrupt ZIP file was not deleted after validation failure"

    @pytest.mark.asyncio
    async def test_valid_zip_does_not_raise(self, tmp_path):
        """A valid ZIP file passes validation and proceeds to extraction."""
        import zipfile as _zipfile
        from shared.connectors.tse import _TSEJobCfg, _download_tse_dataset

        cfg = _TSEJobCfg(
            zip_dir="prestacao_contas",
            zip_prefix="prestacao_de_contas_eleitorais_candidatos",
            csv_prefix="despesas_contratadas_candidatos",
        )
        year = 2024
        zip_filename = f"{cfg.zip_prefix}_{year}.zip"
        zip_path = tmp_path / zip_filename

        # Create a minimal valid ZIP with a matching CSV
        csv_name = f"despesas_contratadas_candidatos_{year}_BRASIL.csv"
        with _zipfile.ZipFile(str(zip_path), "w") as zf:
            zf.writestr(csv_name, "col1;col2\nval1;val2\n")

        # Should not raise — returns path to extracted CSV
        csv_path = await _download_tse_dataset(cfg, year, str(tmp_path))
        assert csv_path.endswith(csv_name) or csv_name in csv_path


# ── Integration: Portal Transparência (real API) ────────────────────

class TestPortalTransparenciaIntegration:
    """Integration tests hitting the real Portal Transparência API.

    Run with: pytest -m integration
    Skip with: pytest -m "not integration"
    """

    @pytest.fixture(autouse=True)
    def skip_without_token(self):
        from shared.config import settings
        if not settings.PORTAL_TRANSPARENCIA_TOKEN:
            pytest.skip("PORTAL_TRANSPARENCIA_TOKEN not set")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_fetch_sancoes_ceis(self):
        c = get_connector("portal_transparencia")
        job = JobSpec(name="pt_sancoes_ceis_cnep", description="", domain="sancao")
        items, cursor = await c.fetch(job, params={"pagina": 1})
        assert isinstance(items, list)
        if items:
            assert items[0].data  # has data
            result = c.normalize(job, items)
            assert len(result.entities) >= 1
            assert len(result.events) >= 1

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_fetch_emendas(self):
        c = get_connector("portal_transparencia")
        job = JobSpec(name="pt_emendas", description="", domain="emenda")
        items, _ = await c.fetch(job, params={"ano": 2024})
        assert isinstance(items, list)


class TestCamaraIntegration:
    """Integration tests hitting the real Câmara API (public, no auth)."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_fetch_deputados(self):
        c = get_connector("camara")
        job = JobSpec(name="camara_deputados", description="", domain="legislativo")
        items, _ = await c.fetch(job)
        assert len(items) > 0
        result = c.normalize(job, items)
        assert len(result.entities) > 0
        assert result.entities[0].type == "person"
