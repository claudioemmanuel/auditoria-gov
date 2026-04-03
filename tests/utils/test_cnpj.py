from shared.utils.cnpj import clean_cnpj, format_cnpj, validate_cnpj


class TestCleanCnpj:
    def test_removes_dots_and_slashes(self):
        assert clean_cnpj("11.222.333/0001-81") == "11222333000181"

    def test_already_clean(self):
        assert clean_cnpj("11222333000181") == "11222333000181"

    def test_empty(self):
        assert clean_cnpj("") == ""

    def test_removes_all_non_digits(self):
        assert clean_cnpj("abc11.222def/333-0001ghi81") == "11222333000181"


class TestFormatCnpj:
    def test_formats_correctly(self):
        assert format_cnpj("11222333000181") == "11.222.333/0001-81"

    def test_already_formatted(self):
        assert format_cnpj("11.222.333/0001-81") == "11.222.333/0001-81"

    def test_short_cnpj_unchanged(self):
        assert format_cnpj("123") == "123"

    def test_empty(self):
        assert format_cnpj("") == ""


class TestValidateCnpj:
    def test_valid_cnpj(self):
        # 11.222.333/0001-81 is a valid CNPJ
        assert validate_cnpj("11222333000181") is True

    def test_valid_cnpj_formatted(self):
        assert validate_cnpj("11.222.333/0001-81") is True

    def test_invalid_check_digit_1(self):
        assert validate_cnpj("11222333000191") is False

    def test_invalid_check_digit_2(self):
        assert validate_cnpj("11222333000182") is False

    def test_all_same_digits(self):
        assert validate_cnpj("11111111111111") is False

    def test_too_short(self):
        assert validate_cnpj("123") is False

    def test_too_long(self):
        assert validate_cnpj("112223330001811") is False

    def test_empty(self):
        assert validate_cnpj("") is False

    def test_all_zeros_invalid(self):
        assert validate_cnpj("00000000000000") is False
