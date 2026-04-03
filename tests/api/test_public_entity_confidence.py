"""Tests for cluster_confidence exposure in public entity endpoints (P1.4)."""
import uuid
from types import SimpleNamespace

import pytest

from api.app.routers import public


# ── /entity/search ────────────────────────────────────────────────────────────

def _fake_search_result(cluster_confidence=85):
    return [
        {
            "entity_id": str(uuid.uuid4()),
            "name": "EMPRESA ALFA LTDA",
            "name_normalized": "empresa alfa ltda",
            "type": "company",
            "cnpj": "12345678000100",
            "cpf": None,
            "cluster_id": str(uuid.uuid4()),
            "score": 0.92,
            "cluster_confidence": cluster_confidence,
        }
    ]


@pytest.mark.asyncio
async def test_entity_search_includes_cluster_confidence(monkeypatch):
    async def _fake(*_a, **_kw):
        return _fake_search_result(cluster_confidence=85)

    monkeypatch.setattr(public, "search_entities", _fake)
    result = await public.entity_search(session=None, q="EMPRESA ALFA")
    assert len(result) == 1
    assert "cluster_confidence" in result[0]
    assert result[0]["cluster_confidence"] == 85


@pytest.mark.asyncio
async def test_entity_search_cluster_confidence_can_be_none(monkeypatch):
    """Entities not involved in any ER merge have cluster_confidence=None."""
    async def _fake(*_a, **_kw):
        return _fake_search_result(cluster_confidence=None)

    monkeypatch.setattr(public, "search_entities", _fake)
    result = await public.entity_search(session=None, q="EMPRESA ALFA")
    assert result[0]["cluster_confidence"] is None


# ── /entity/{entity_id} ───────────────────────────────────────────────────────

def _fake_entity(cluster_confidence=72):
    return SimpleNamespace(
        id=uuid.uuid4(),
        type="company",
        name="EMPRESA BETA SA",
        identifiers={"cnpj": "98765432000181"},
        attrs={"municipio": "BELO HORIZONTE"},
        cluster_id=uuid.uuid4(),
        cluster_confidence=cluster_confidence,
        aliases=[],
    )


@pytest.mark.asyncio
async def test_entity_detail_includes_cluster_confidence(monkeypatch):
    entity = _fake_entity(cluster_confidence=72)

    async def _fake(*_a, **_kw):
        return entity

    monkeypatch.setattr(public, "get_entity_by_id", _fake)
    result = await public.entity_detail(entity_id=entity.id, session=None)
    assert "cluster_confidence" in result
    assert result["cluster_confidence"] == 72


@pytest.mark.asyncio
async def test_entity_detail_cluster_confidence_none_for_unmerged(monkeypatch):
    """Entities that were not merged by ER have cluster_confidence=None."""
    entity = _fake_entity(cluster_confidence=None)
    entity.cluster_id = None

    async def _fake(*_a, **_kw):
        return entity

    monkeypatch.setattr(public, "get_entity_by_id", _fake)
    result = await public.entity_detail(entity_id=entity.id, session=None)
    assert result["cluster_confidence"] is None
    assert result["cluster_id"] is None
