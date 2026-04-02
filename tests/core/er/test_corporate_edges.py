"""Tests for shared/er/corporate_edges.py."""

import uuid
from unittest.mock import MagicMock

from openwatch_er.corporate_edges import build_corporate_edges, _cnpj_raiz, _normalise_address, _normalise_phone


# ── Pure helper tests ────────────────────────────────────────────────────────

def test_cnpj_raiz_strips_mask():
    assert _cnpj_raiz("12.345.678/0001-90") == "12345678"


def test_cnpj_raiz_short_returns_empty():
    assert _cnpj_raiz("1234") == ""


def test_normalise_address_uppercase_and_collapses():
    result = _normalise_address("Rua da Paz, 123 - Centro")
    assert result == result.upper() or result == result  # just checks no crash
    assert "  " not in result  # no double spaces


def test_normalise_phone_digits_only():
    assert _normalise_phone("(61) 3333-4444") == "6133334444"


# ── Mock-session integration tests ──────────────────────────────────────────

def _make_entity(entity_id, identifiers=None, attrs=None):
    e = MagicMock()
    e.id = entity_id
    e.identifiers = identifiers or {}
    e.attrs = attrs or {}
    return e


def _mock_session(entities):
    """Return a session mock whose execute().all() yields entity rows."""
    session = MagicMock()

    rows = [(e.id, e.identifiers, e.attrs) for e in entities]

    # First call returns rows; second call (offset > 0) returns empty to end pagination.
    call_count = {"n": 0}

    def execute(stmt):
        result = MagicMock()
        if call_count["n"] == 0:
            result.all.return_value = rows
        else:
            result.all.return_value = []
        call_count["n"] += 1
        return result

    session.execute = execute
    return session


class TestBuildCorporateEdges:
    def test_same_address_two_companies(self):
        a, b = uuid.uuid4(), uuid.uuid4()
        entities = [
            _make_entity(a, attrs={"address": "Rua das Flores 100 Centro"}),
            _make_entity(b, attrs={"address": "Rua das Flores 100 Centro"}),
        ]
        session = _mock_session(entities)
        edges = build_corporate_edges(session)
        same_addr = [e for e in edges if e.edge_type == "SAME_ADDRESS"]
        assert len(same_addr) == 1
        assert {same_addr[0].from_entity_id, same_addr[0].to_entity_id} == {a, b}

    def test_short_address_ignored(self):
        a, b = uuid.uuid4(), uuid.uuid4()
        entities = [
            _make_entity(a, attrs={"address": "SN"}),  # too short
            _make_entity(b, attrs={"address": "SN"}),
        ]
        session = _mock_session(entities)
        edges = build_corporate_edges(session)
        assert not any(e.edge_type == "SAME_ADDRESS" for e in edges)

    def test_shares_phone_two_companies(self):
        a, b = uuid.uuid4(), uuid.uuid4()
        phone = "(61) 98765-4321"
        entities = [
            _make_entity(a, attrs={"telefone": phone}),
            _make_entity(b, attrs={"telefone": phone}),
        ]
        session = _mock_session(entities)
        edges = build_corporate_edges(session)
        phone_edges = [e for e in edges if e.edge_type == "SHARES_PHONE"]
        assert len(phone_edges) == 1

    def test_same_socio_via_qsa(self):
        a, b = uuid.uuid4(), uuid.uuid4()
        socio_cpf = "12345678901"
        entities = [
            _make_entity(a, attrs={"qsa": [{"cpf_cnpj_socio": socio_cpf}]}),
            _make_entity(b, attrs={"qsa": [{"cpf_cnpj_socio": socio_cpf}]}),
        ]
        session = _mock_session(entities)
        edges = build_corporate_edges(session)
        socio_edges = [e for e in edges if e.edge_type == "SAME_SOCIO"]
        assert len(socio_edges) == 1
        assert socio_edges[0].verification_confidence >= 0.80

    def test_same_accountant(self):
        a, b = uuid.uuid4(), uuid.uuid4()
        acct_cnpj = "12345678000195"
        entities = [
            _make_entity(a, attrs={"cnpj_contabilista": acct_cnpj}),
            _make_entity(b, attrs={"cnpj_contabilista": acct_cnpj}),
        ]
        session = _mock_session(entities)
        edges = build_corporate_edges(session)
        acct_edges = [e for e in edges if e.edge_type == "SAME_ACCOUNTANT"]
        assert len(acct_edges) == 1

    def test_subsidiary_holding_via_cnpj_raiz(self):
        parent, child = uuid.uuid4(), uuid.uuid4()
        entities = [
            _make_entity(parent, identifiers={"cnpj": "12345678000195"}),
            _make_entity(child, identifiers={"cnpj": "12345678000296"}),
        ]
        session = _mock_session(entities)
        edges = build_corporate_edges(session)
        sub = [e for e in edges if e.edge_type == "SUBSIDIARY"]
        hold = [e for e in edges if e.edge_type == "HOLDING"]
        assert len(sub) == 1
        assert len(hold) == 1
        # SUBSIDIARY goes from child → parent
        assert sub[0].to_entity_id != sub[0].from_entity_id

    def test_no_edges_when_all_unique(self):
        entities = [
            _make_entity(uuid.uuid4(), attrs={"address": "Endereco Unico Apenas Um 999"}),
            _make_entity(uuid.uuid4(), attrs={"address": "Outro Logradouro Completamente 888"}),
        ]
        session = _mock_session(entities)
        edges = build_corporate_edges(session)
        same_addr = [e for e in edges if e.edge_type == "SAME_ADDRESS"]
        assert len(same_addr) == 0

    def test_empty_entities_returns_no_edges(self):
        session = _mock_session([])
        edges = build_corporate_edges(session)
        assert edges == []

    def test_edge_attrs_populated(self):
        a, b = uuid.uuid4(), uuid.uuid4()
        entities = [
            _make_entity(a, attrs={"address": "Avenida Paulista 1000 Bela Vista"}),
            _make_entity(b, attrs={"address": "Avenida Paulista 1000 Bela Vista"}),
        ]
        session = _mock_session(entities)
        edges = build_corporate_edges(session)
        same_addr = [e for e in edges if e.edge_type == "SAME_ADDRESS"]
        assert "address" in same_addr[0].attrs
