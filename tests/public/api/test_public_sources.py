"""Tests for GET /sources endpoint (governance transparency)."""

from datetime import datetime, timezone

import pytest

from api.app.routers import public


def _fake_public_sources():
    """Build a realistic response for monkeypatching."""
    return {
        "items": [
            {
                "connector": "portal_transparencia",
                "job": "pt_sancoes_ceis_cnep",
                "domain": "sancao",
                "base_url": "https://api.portaldatransparencia.gov.br",
                "is_government": True,
                "veracity": {
                    "government_domain": 1.0,
                    "legal_authority": 1.0,
                    "public_availability": 1.0,
                    "official_api_documented": 1.0,
                    "metadata_traceability": 0.95,
                    "composite_score": 0.995,
                    "label": "official",
                },
                "status": "ok",
                "freshness_lag_hours": 2.5,
                "total_items": 50000,
                "compliance_status": "ok",
            },
            {
                "connector": "senado",
                "job": "senado_ceaps",
                "domain": "despesa",
                "base_url": "https://legis.senado.leg.br",
                "is_government": True,
                "veracity": {
                    "government_domain": 1.0,
                    "legal_authority": 1.0,
                    "public_availability": 1.0,
                    "official_api_documented": 0.85,
                    "metadata_traceability": 0.85,
                    "composite_score": 0.97,
                    "label": "official",
                },
                "status": "ok",
                "freshness_lag_hours": 12.0,
                "total_items": 10000,
                "compliance_status": "ok",
            },
            {
                "connector": "querido_diario",
                "job": "qd_gazettes",
                "domain": "diario_oficial",
                "base_url": "https://api.queridodiario.ok.org.br",
                "is_government": False,
                "veracity": {
                    "government_domain": 0.0,
                    "legal_authority": 0.50,
                    "public_availability": 1.0,
                    "official_api_documented": 0.90,
                    "metadata_traceability": 0.70,
                    "composite_score": 0.435,
                    "label": "acceptable",
                },
                "status": "warning",
                "freshness_lag_hours": 36.0,
                "total_items": 8000,
                "compliance_status": "ok",
            },
        ],
        "total": 3,
        "policy_version": "1.0",
        "domain_whitelist": [".def.br", ".gov.br", ".jus.br", ".leg.br", ".mil.br", ".mp.br"],
        "controlled_exceptions": [
            {
                "domain": "api.queridodiario.ok.org.br",
                "justification": "Community project for municipal gazettes",
                "max_veracity": 0.85,
                "review_by": "2026-09-04",
            }
        ],
        "generated_at": datetime.now(timezone.utc),
    }


@pytest.mark.asyncio
async def test_returns_all_connectors(monkeypatch):
    async def _fake(*_a, **_kw):
        return _fake_public_sources()

    monkeypatch.setattr(public, "get_public_sources", _fake)
    payload = await public.public_sources(session=None)
    assert payload["total"] == 3
    connectors = {item["connector"] for item in payload["items"]}
    assert "portal_transparencia" in connectors
    assert "senado" in connectors


@pytest.mark.asyncio
async def test_includes_veracity_scores(monkeypatch):
    async def _fake(*_a, **_kw):
        return _fake_public_sources()

    monkeypatch.setattr(public, "get_public_sources", _fake)
    payload = await public.public_sources(session=None)
    for item in payload["items"]:
        assert "veracity" in item
        assert item["veracity"] is not None
        assert "composite_score" in item["veracity"]
        assert "label" in item["veracity"]


@pytest.mark.asyncio
async def test_includes_domain_whitelist(monkeypatch):
    async def _fake(*_a, **_kw):
        return _fake_public_sources()

    monkeypatch.setattr(public, "get_public_sources", _fake)
    payload = await public.public_sources(session=None)
    assert ".gov.br" in payload["domain_whitelist"]
    assert ".leg.br" in payload["domain_whitelist"]
    assert len(payload["controlled_exceptions"]) == 1
    assert payload["controlled_exceptions"][0]["domain"] == "api.queridodiario.ok.org.br"


@pytest.mark.asyncio
async def test_no_codante_urls(monkeypatch):
    async def _fake(*_a, **_kw):
        return _fake_public_sources()

    monkeypatch.setattr(public, "get_public_sources", _fake)
    payload = await public.public_sources(session=None)
    for item in payload["items"]:
        if item.get("base_url"):
            assert "codante" not in item["base_url"].lower()
