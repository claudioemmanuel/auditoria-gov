import hashlib
import hmac

from shared.utils.hashing import hash_cpf, mask_cpf


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


class TestMaskCpf:
    def test_basic_mask(self):
        assert mask_cpf("12345678900") == "***.***789-00"

    def test_formatted_cpf(self):
        assert mask_cpf("123.456.789-00") == "***.***789-00"

    def test_short_cpf(self):
        assert mask_cpf("123") == "***.***.***-**"

    def test_empty_cpf(self):
        assert mask_cpf("") == "***.***.***-**"

    def test_long_cpf(self):
        assert mask_cpf("1234567890012") == "***.***.***-**"
