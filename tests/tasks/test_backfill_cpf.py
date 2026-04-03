from worker.tasks.backfill_cpf import _extract_cpf_from_raw


class TestExtractCpfFromRaw:
    def test_portal_transparencia_cpf(self):
        raw = {"cpf": "215.768.058-67", "nome": "Joao"}
        assert _extract_cpf_from_raw(raw, "portal_transparencia") == "21576805867"

    def test_portal_transparencia_cpf_formatado(self):
        raw = {"cpfFormatado": "215.768.058-67"}
        assert _extract_cpf_from_raw(raw, "portal_transparencia") == "21576805867"

    def test_tse_nr_cpf_candidato(self):
        raw = {"NR_CPF_CANDIDATO": "12345678901"}
        assert _extract_cpf_from_raw(raw, "tse") == "12345678901"

    def test_compras_gov_cnpj_cpf_with_cpf(self):
        raw = {"cnpjCpf": "98765432100"}
        assert _extract_cpf_from_raw(raw, "compras_gov") == "98765432100"

    def test_compras_gov_cnpj_cpf_with_cnpj_returns_none(self):
        raw = {"cnpjCpf": "12345678000199"}
        assert _extract_cpf_from_raw(raw, "compras_gov") is None

    def test_pncp_ni_fornecedor_cpf(self):
        raw = {"niFornecedor": "12345678901"}
        assert _extract_cpf_from_raw(raw, "pncp") == "12345678901"

    def test_pncp_ni_fornecedor_cnpj_returns_none(self):
        raw = {"niFornecedor": "12345678000199"}
        assert _extract_cpf_from_raw(raw, "pncp") is None

    def test_unknown_connector_returns_none(self):
        raw = {"cpf": "12345678901"}
        assert _extract_cpf_from_raw(raw, "unknown_connector") is None

    def test_empty_raw_data(self):
        assert _extract_cpf_from_raw({}, "portal_transparencia") is None

    def test_none_value_in_raw(self):
        raw = {"cpf": None}
        assert _extract_cpf_from_raw(raw, "portal_transparencia") is None
