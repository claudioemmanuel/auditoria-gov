from shared.utils.text import normalize_name, strip_accents, clean_whitespace


class TestStripAccents:
    def test_removes_accents(self):
        assert strip_accents("São Paulo") == "Sao Paulo"

    def test_removes_tilde(self):
        assert strip_accents("João") == "Joao"

    def test_removes_cedilla(self):
        assert strip_accents("Açúcar") == "Acucar"

    def test_no_accents(self):
        assert strip_accents("Hello") == "Hello"

    def test_empty_string(self):
        assert strip_accents("") == ""

    def test_multiple_accents(self):
        assert strip_accents("àáâãäèéêëìíîïòóôõöùúûü") == "aaaaaeeeeiiiiooooouu" + "uu"


class TestCleanWhitespace:
    def test_collapses_spaces(self):
        assert clean_whitespace("hello   world") == "hello world"

    def test_strips_ends(self):
        assert clean_whitespace("  hello  ") == "hello"

    def test_tabs_and_newlines(self):
        assert clean_whitespace("hello\t\n  world") == "hello world"

    def test_empty_string(self):
        assert clean_whitespace("") == ""

    def test_single_word(self):
        assert clean_whitespace("hello") == "hello"

    def test_only_whitespace(self):
        assert clean_whitespace("   ") == ""


class TestNormalizeName:
    def test_uppercases(self):
        assert normalize_name("hello") == "HELLO"

    def test_strips_accents_and_uppercases(self):
        assert normalize_name("São Paulo") == "SAO PAULO"

    def test_cleans_whitespace(self):
        assert normalize_name("  joão   silva  ") == "JOAO SILVA"

    def test_combined(self):
        assert normalize_name("  Açúcar  Cristal  ") == "ACUCAR CRISTAL"

    def test_empty_string(self):
        assert normalize_name("") == ""
