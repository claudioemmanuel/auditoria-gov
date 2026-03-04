"""Tests for domain whitelist enforcement."""

import pytest

from shared.connectors.domain_guard import (
    DomainNotAllowedError,
    is_government_domain,
    validate_domain,
)


class TestValidateDomain:
    def test_gov_br_allowed(self):
        score = validate_domain("https://api.portaldatransparencia.gov.br/api-de-dados")
        assert score == 1.0

    def test_leg_br_allowed(self):
        score = validate_domain("https://legis.senado.leg.br/dadosabertos")
        assert score == 1.0

    def test_jus_br_allowed(self):
        score = validate_domain("https://portal.stf.jus.br/api")
        assert score == 1.0

    def test_mil_br_allowed(self):
        score = validate_domain("https://dados.eb.mil.br/api")
        assert score == 1.0

    def test_mp_br_allowed(self):
        score = validate_domain("https://portal.mpf.mp.br/api")
        assert score == 1.0

    def test_def_br_allowed(self):
        score = validate_domain("https://dados.defesa.def.br/api")
        assert score == 1.0

    def test_querido_diario_exception(self):
        score = validate_domain("https://api.queridodiario.ok.org.br/gazettes")
        assert score == 0.85

    def test_codante_blocked(self):
        with pytest.raises(DomainNotAllowedError) as exc_info:
            validate_domain("https://apis.codante.io/senator-expenses")
        assert exc_info.value.domain == "apis.codante.io"

    def test_random_domain_blocked(self):
        with pytest.raises(DomainNotAllowedError):
            validate_domain("https://example.com/api")

    def test_github_blocked(self):
        with pytest.raises(DomainNotAllowedError):
            validate_domain("https://api.github.com/repos")


class TestIsGovernmentDomain:
    def test_is_government_domain_true(self):
        assert is_government_domain("https://compras.dados.gov.br") is True
        assert is_government_domain("https://dadosabertos.camara.leg.br/api/v2") is True

    def test_is_government_domain_false(self):
        assert is_government_domain("https://apis.codante.io/senator-expenses") is False
        assert is_government_domain("https://api.queridodiario.ok.org.br") is False
        assert is_government_domain("https://example.com") is False
