from shared.er.normalize import normalize_entity_for_matching


class TestNormalizeEntityForMatching:
    def test_name_normalization(self):
        result = normalize_entity_for_matching("São Paulo Ltda", {})
        assert result["name_norm"] == "SAO PAULO LTDA"

    def test_cnpj_cleaned(self):
        result = normalize_entity_for_matching("Test", {"cnpj": "11.222.333/0001-81"})
        assert result["cnpj"] == "11222333000181"

    def test_cnpj_none_when_missing(self):
        result = normalize_entity_for_matching("Test", {})
        assert result["cnpj"] is None

    def test_cpf_hash_passthrough(self):
        result = normalize_entity_for_matching("Test", {"cpf_hash": "abc123"})
        assert result["cpf_hash"] == "abc123"

    def test_cpf_hash_none_when_missing(self):
        result = normalize_entity_for_matching("Test", {})
        assert result["cpf_hash"] is None

    def test_tokens_extracted(self):
        result = normalize_entity_for_matching("Maria Silva Santos", {})
        assert "MARIA" in result["tokens"]
        assert "SILVA" in result["tokens"]
        assert "SANTOS" in result["tokens"]

    def test_stop_words_removed(self):
        result = normalize_entity_for_matching("Maria da Silva", {})
        assert "DA" not in result["tokens"]
        assert "MARIA" in result["tokens"]
        assert "SILVA" in result["tokens"]

    def test_common_business_stop_words(self):
        result = normalize_entity_for_matching("ACME Ltda ME", {})
        assert "LTDA" not in result["tokens"]
        assert "ME" not in result["tokens"]
        assert "ACME" in result["tokens"]

    def test_empty_name(self):
        result = normalize_entity_for_matching("", {})
        assert result["name_norm"] == ""
        assert result["tokens"] == set()
