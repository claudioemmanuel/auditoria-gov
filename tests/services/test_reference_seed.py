"""Tests for reference_data seed service."""

import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shared.services.reference_seed import (
    _upsert_ref,
    seed_ibge_municipios,
    seed_ibge_ufs,
    seed_siape_orgaos,
    _parse_rf_csv,
)


class TestUpsertRef:
    def test_upsert_executes_insert_statement(self):
        session = MagicMock()
        _upsert_ref(session, "ibge_uf", code="SP", name="São Paulo", parent_code="SE")
        session.execute.assert_called_once()

    def test_upsert_idempotent(self):
        """Calling upsert twice should execute two statements (ON CONFLICT UPDATE)."""
        session = MagicMock()
        _upsert_ref(session, "ibge_uf", code="SP", name="São Paulo")
        _upsert_ref(session, "ibge_uf", code="SP", name="São Paulo (updated)")
        assert session.execute.call_count == 2

    def test_upsert_with_attrs(self):
        session = MagicMock()
        _upsert_ref(
            session, "ibge_municipio",
            code="3550308", name="São Paulo",
            attrs={"regiao": "Sudeste"},
        )
        session.execute.assert_called_once()


class TestSeedIbgeMunicipios:
    @pytest.mark.asyncio
    async def test_seed_ibge_municipios(self):
        mock_data = [
            {
                "id": 3550308,
                "nome": "São Paulo",
                "microrregiao": {
                    "mesorregiao": {
                        "UF": {
                            "sigla": "SP",
                            "nome": "São Paulo",
                            "regiao": {"nome": "Sudeste"},
                        }
                    }
                },
            },
            {
                "id": 3304557,
                "nome": "Rio de Janeiro",
                "microrregiao": {
                    "mesorregiao": {
                        "UF": {
                            "sigla": "RJ",
                            "nome": "Rio de Janeiro",
                            "regiao": {"nome": "Sudeste"},
                        }
                    }
                },
            },
        ]

        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_data
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        session = MagicMock()

        with patch("shared.services.reference_seed.httpx.AsyncClient", return_value=mock_client):
            count = await seed_ibge_municipios(session)

        assert count == 2
        session.commit.assert_called_once()
        assert session.execute.call_count == 2


class TestSeedIbgeUfs:
    @pytest.mark.asyncio
    async def test_seed_ibge_ufs(self):
        mock_data = [
            {"id": 35, "sigla": "SP", "nome": "São Paulo", "regiao": {"sigla": "SE", "nome": "Sudeste"}},
            {"id": 33, "sigla": "RJ", "nome": "Rio de Janeiro", "regiao": {"sigla": "SE", "nome": "Sudeste"}},
        ]

        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_data
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        session = MagicMock()

        with patch("shared.services.reference_seed.httpx.AsyncClient", return_value=mock_client):
            count = await seed_ibge_ufs(session)

        assert count == 2
        session.commit.assert_called_once()


class TestSeedSiapeOrgaos:
    @pytest.mark.asyncio
    async def test_seed_siape_orgaos(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [
            {"codigo": "26000", "descricao": "MINISTERIO DA EDUCACAO"},
            {"codigo": "26100", "descricao": "MINISTERIO DA SAUDE"},
        ]
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        session = MagicMock()

        with patch(
            "shared.services.reference_seed.portal_transparencia_client",
            return_value=mock_client,
        ):
            count = await seed_siape_orgaos(session)

        assert count == 2
        session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_seed_siape_orgaos_empty_response(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = []
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        session = MagicMock()

        with patch(
            "shared.services.reference_seed.portal_transparencia_client",
            return_value=mock_client,
        ):
            count = await seed_siape_orgaos(session)

        assert count == 0


class TestParseRfCsv:
    def test_parse_rf_csv(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = os.path.join(tmpdir, "CNAES.csv")
            with open(csv_path, "w", encoding="iso-8859-1") as f:
                f.write("0111301;Cultivo de arroz\n")
                f.write("0111302;Cultivo de milho\n")
                f.write("0111303;Cultivo de trigo\n")

            session = MagicMock()
            count = _parse_rf_csv(session, tmpdir, "CNAES", category="cnae")
            assert count == 3
            assert session.execute.call_count == 3

    def test_parse_rf_csv_file_not_found(self):
        session = MagicMock()
        count = _parse_rf_csv(session, "/nonexistent", "CNAES", category="cnae")
        assert count == 0

    def test_parse_rf_csv_skips_empty_rows(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = os.path.join(tmpdir, "Naturezas.csv")
            with open(csv_path, "w", encoding="iso-8859-1") as f:
                f.write("1015;Orgao Publico Federal\n")
                f.write(";\n")  # Empty code and name
                f.write(";Sem codigo\n")  # Empty code
                f.write("1023;Orgao Publico Estadual\n")

            session = MagicMock()
            count = _parse_rf_csv(session, tmpdir, "Naturezas", category="natureza_juridica")
            assert count == 2
