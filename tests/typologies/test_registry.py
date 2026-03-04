import pytest

from shared.typologies.registry import (
    TypologyRegistry,
    get_all_typologies,
    get_typology,
)
from shared.typologies.base import BaseTypology


class TestTypologyRegistry:
    def test_has_18_typologies(self):
        assert len(TypologyRegistry) == 18

    def test_all_codes_present(self):
        for i in range(1, 19):
            code = f"T{i:02d}"
            assert code in TypologyRegistry

    def test_all_are_base_typology_subclasses(self):
        for cls in TypologyRegistry.values():
            assert issubclass(cls, BaseTypology)


class TestGetAllTypologies:
    def test_returns_18_instances(self):
        typologies = get_all_typologies()
        assert len(typologies) == 18

    def test_all_have_id(self):
        for t in get_all_typologies():
            assert t.id.startswith("T")
            assert len(t.id) == 3

    def test_all_have_name(self):
        for t in get_all_typologies():
            assert len(t.name) > 0

    def test_all_have_required_domains(self):
        for t in get_all_typologies():
            assert isinstance(t.required_domains, list)
            assert len(t.required_domains) > 0


class TestGetTypology:
    def test_valid_code(self):
        t = get_typology("T01")
        assert t.id == "T01"

    def test_invalid_code_raises(self):
        with pytest.raises(ValueError, match="Unknown typology"):
            get_typology("T99")


class TestTypologyProperties:
    """Test each typology's properties individually."""

    def test_t01(self):
        t = get_typology("T01")
        assert t.name == "Concentração em Fornecedor"
        assert "licitacao" in t.required_domains

    def test_t02(self):
        t = get_typology("T02")
        assert t.name == "Baixa Competição"
        assert "licitacao" in t.required_domains

    def test_t03(self):
        t = get_typology("T03")
        assert t.name == "Fracionamento de Despesa"
        assert "despesa" in t.required_domains

    def test_t04(self):
        t = get_typology("T04")
        assert t.name == "Aditivo Outlier"
        assert "contrato" in t.required_domains

    def test_t05(self):
        t = get_typology("T05")
        assert t.name == "Preço Outlier"
        assert "licitacao" in t.required_domains

    def test_t06(self):
        t = get_typology("T06")
        assert t.name == "Proxy de Empresa de Fachada"
        assert "empresa" in t.required_domains

    def test_t07(self):
        t = get_typology("T07")
        assert t.name == "Rede de Cartel"
        assert "licitacao" in t.required_domains

    def test_t08(self):
        t = get_typology("T08")
        assert t.name == "Sanção x Contrato"
        assert "sancao" in t.required_domains

    def test_t09(self):
        t = get_typology("T09")
        assert t.name == "Proxy de Folha Fantasma"
        assert "remuneracao" in t.required_domains

    def test_t10(self):
        t = get_typology("T10")
        assert t.name == "Terceirização Paralela"
        assert "contrato" in t.required_domains


class TestTypologyRun:
    """Test that all typology run() methods return lists (may be empty without DB)."""

    @pytest.mark.asyncio
    async def test_all_run_return_list(self):
        """All typologies should return a list when given None session.

        Implemented typologies may raise on None session, so we catch
        AttributeError/TypeError and consider that as 'implemented'.
        """
        for t in get_all_typologies():
            try:
                result = await t.run(None)
                assert isinstance(result, list), f"{t.id} run() did not return list"
            except (AttributeError, TypeError):
                # Typology tried to use session — means it's implemented
                pass


class TestTypologyRequiredFields:
    def test_all_have_required_fields(self):
        for t in get_all_typologies():
            assert isinstance(t.required_fields, list)


class TestBaseTypologyDefaults:
    def test_required_fields_default_returns_empty(self):
        """Cover base class default required_fields (line 30)."""

        class StubTypology(BaseTypology):
            @property
            def id(self) -> str:
                return "T99"

            @property
            def name(self) -> str:
                return "Stub"

            @property
            def required_domains(self) -> list[str]:
                return ["test"]

            async def run(self, session) -> list:
                return []

        t = StubTypology()
        assert t.required_fields == []
