import uuid

from shared.er.matching import (
    deterministic_match,
    probabilistic_match,
    _jaro_winkler_similarity,
)


def _entity(name="Test", identifiers=None, attrs=None):
    return {
        "id": uuid.uuid4(),
        "name": name,
        "identifiers": identifiers or {},
        "attrs": attrs or {},
    }


class TestJaroWinklerSimilarity:
    def test_identical_strings(self):
        assert _jaro_winkler_similarity("hello", "hello") == 1.0

    def test_empty_strings(self):
        assert _jaro_winkler_similarity("", "") == 1.0

    def test_one_empty(self):
        assert _jaro_winkler_similarity("hello", "") == 0.0
        assert _jaro_winkler_similarity("", "hello") == 0.0

    def test_similar_strings(self):
        sim = _jaro_winkler_similarity("MARTHA", "MARHTA")
        assert sim > 0.9

    def test_different_strings(self):
        sim = _jaro_winkler_similarity("ABC", "XYZ")
        assert sim < 0.5

    def test_prefix_boost(self):
        # Winkler boost for shared prefix
        sim1 = _jaro_winkler_similarity("JOHNSON", "JONHSON")
        sim2 = _jaro_winkler_similarity("XOHNSON", "XONHSON")
        # Both should be similar but prefix boost helps
        assert sim1 > 0.9

    def test_completely_different(self):
        sim = _jaro_winkler_similarity("ABCDEF", "ZYXWVU")
        assert sim < 0.5

    def test_single_char(self):
        assert _jaro_winkler_similarity("A", "A") == 1.0
        assert _jaro_winkler_similarity("A", "B") == 0.0


class TestDeterministicMatch:
    def test_cnpj_match(self):
        a = _entity("Company A", {"cnpj": "11222333000181"})
        b = _entity("Company B", {"cnpj": "11222333000181"})
        result = deterministic_match(a, b)
        assert result is not None
        assert result.match_type == "deterministic"
        assert result.score == 1.0
        assert "CNPJ" in result.reason

    def test_cnpj_no_match(self):
        a = _entity("Company A", {"cnpj": "11222333000181"})
        b = _entity("Company B", {"cnpj": "99888777000199"})
        result = deterministic_match(a, b)
        assert result is None

    def test_cpf_hash_match(self):
        a = _entity("Person A", {"cpf_hash": "abc123"})
        b = _entity("Person B", {"cpf_hash": "abc123"})
        result = deterministic_match(a, b)
        assert result is not None
        assert result.score == 1.0
        assert "CPF" in result.reason

    def test_cpf_hash_no_match(self):
        a = _entity("Person A", {"cpf_hash": "abc123"})
        b = _entity("Person B", {"cpf_hash": "xyz789"})
        result = deterministic_match(a, b)
        assert result is None

    def test_cpf_raw_match_when_hash_absent(self):
        a = _entity("Person A", {"cpf": "215.768.058-67"})
        b = _entity("Person B", {"cpf": "21576805867"})
        result = deterministic_match(a, b)
        assert result is not None
        assert result.score == 1.0
        assert "CPF" in result.reason

    def test_no_identifiers(self):
        a = _entity("Company A")
        b = _entity("Company B")
        result = deterministic_match(a, b)
        assert result is None

    def test_one_has_cnpj_other_doesnt(self):
        a = _entity("A", {"cnpj": "11222333000181"})
        b = _entity("B", {})
        result = deterministic_match(a, b)
        assert result is None


class TestProbabilisticMatch:
    def test_exact_name_match(self):
        a = _entity("EMPRESA TESTE")
        b = _entity("EMPRESA TESTE")
        result = probabilistic_match(a, b, threshold=0.8)
        assert result is not None
        assert result.match_type == "probabilistic"
        assert result.score >= 0.8

    def test_similar_name_match(self):
        a = _entity("EMPRESA TESTE LTDA")
        b = _entity("EMPRESA TESTE")
        result = probabilistic_match(a, b, threshold=0.7)
        assert result is not None

    def test_different_names_no_match(self):
        a = _entity("EMPRESA ABC")
        b = _entity("COMPANHIA XYZ")
        result = probabilistic_match(a, b, threshold=0.85)
        assert result is None

    def test_boost_from_shared_address(self):
        a = _entity("TEST CORP", attrs={"address": "Rua A, 123"})
        b = _entity("TEST CORP", attrs={"address": "Rua A, 123"})
        result_with = probabilistic_match(a, b, threshold=0.5)

        c = _entity("TEST CORP", attrs={"address": "Rua B, 456"})
        result_without = probabilistic_match(a, c, threshold=0.5)

        assert result_with is not None
        assert result_without is not None
        assert result_with.score >= result_without.score

    def test_boost_from_shared_email(self):
        a = _entity("TEST", attrs={"email": "a@b.com"})
        b = _entity("TEST", attrs={"email": "a@b.com"})
        result = probabilistic_match(a, b, threshold=0.5)
        assert result is not None

    def test_boost_from_shared_phone(self):
        a = _entity("TEST", attrs={"phone": "11999999999"})
        b = _entity("TEST", attrs={"phone": "11999999999"})
        result = probabilistic_match(a, b, threshold=0.5)
        assert result is not None

    def test_high_threshold_requires_strong_match(self):
        a = _entity("EMPRESA ALFA BETA")
        b = _entity("EMPRESA GAMA DELTA")
        result = probabilistic_match(a, b, threshold=0.99)
        assert result is None

    def test_empty_tokens(self):
        a = _entity("")
        b = _entity("")
        result = probabilistic_match(a, b, threshold=0.5)
        # Empty names should still work (name_sim = 1.0, token_sim = 0)
        assert result is not None
