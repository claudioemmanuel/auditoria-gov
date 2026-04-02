import pytest

from openwatch_ai.ner import ExtractedEntity, extract_entities_from_text, _extract_with_regex


class TestExtractWithRegex:
    def test_cnpj_detection(self):
        text = "A empresa 12.345.678/0001-90 foi contratada."
        entities = _extract_with_regex(text)
        cnpj_ents = [e for e in entities if e.label == "CNPJ"]
        assert len(cnpj_ents) == 1
        assert cnpj_ents[0].text == "12.345.678/0001-90"

    def test_cpf_detection(self):
        text = "CPF do responsável: 123.456.789-00."
        entities = _extract_with_regex(text)
        cpf_ents = [e for e in entities if e.label == "CPF"]
        assert len(cpf_ents) == 1
        assert cpf_ents[0].text == "123.456.789-00"

    def test_money_detection(self):
        text = "O valor é de R$ 1.234.567,89 para a obra."
        entities = _extract_with_regex(text)
        money_ents = [e for e in entities if e.label == "MONEY"]
        assert len(money_ents) >= 1

    def test_law_detection(self):
        text = "Conforme Lei 14.133/2021 e Decreto 7.892/2013."
        entities = _extract_with_regex(text)
        law_ents = [e for e in entities if e.label == "LAW"]
        assert len(law_ents) >= 1

    def test_date_detection(self):
        text = "Publicado em 15/03/2024 no diário oficial."
        entities = _extract_with_regex(text)
        date_ents = [e for e in entities if e.label == "DATE"]
        assert len(date_ents) == 1
        assert date_ents[0].text == "15/03/2024"

    def test_no_entities(self):
        text = "Texto simples sem entidades detectáveis."
        entities = _extract_with_regex(text)
        assert isinstance(entities, list)

    def test_multiple_entities(self):
        text = (
            "A empresa 12.345.678/0001-90 recebeu R$ 500.000,00 "
            "conforme Lei 14.133/2021 em 01/01/2024."
        )
        entities = _extract_with_regex(text)
        assert len(entities) >= 3


class TestExtractEntitiesFromText:
    @pytest.mark.asyncio
    async def test_returns_list(self):
        result = await extract_entities_from_text("Texto de teste")
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_deduplicates(self):
        text = "CNPJ 12.345.678/0001-90 e CNPJ 12.345.678/0001-90"
        result = await extract_entities_from_text(text)
        cnpj_ents = [e for e in result if e.label == "CNPJ"]
        assert len(cnpj_ents) == 1  # Deduplicated


class TestExtractedEntity:
    def test_dataclass(self):
        e = ExtractedEntity(
            text="test", label="PERSON", start=0, end=4, confidence=0.9
        )
        assert e.text == "test"
        assert e.label == "PERSON"
        assert e.confidence == 0.9
