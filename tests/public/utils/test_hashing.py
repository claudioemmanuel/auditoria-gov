import hashlib
import hmac

from openwatch_utils.hashing import hash_cpf


class TestHashCpf:
    def test_basic_hash(self):
        result = hash_cpf("123.456.789-00", "salt")
        expected = hmac.new("salt".encode(), "12345678900".encode(), hashlib.sha256).hexdigest()
        assert result == expected

    def test_strips_formatting(self):
        assert hash_cpf("123.456.789-00", "s") == hash_cpf("12345678900", "s")

    def test_different_salt_different_hash(self):
        assert hash_cpf("12345678900", "a") != hash_cpf("12345678900", "b")

    def test_deterministic(self):
        assert hash_cpf("12345678900", "s") == hash_cpf("12345678900", "s")

    def test_empty_cpf(self):
        result = hash_cpf("", "salt")
        expected = hmac.new("salt".encode(), "".encode(), hashlib.sha256).hexdigest()
        assert result == expected
