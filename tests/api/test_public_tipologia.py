"""Tests for GET /public/tipologia and GET /public/tipologia/{code} (P4.3)."""
import pytest

from api.app.routers import public


@pytest.mark.asyncio
async def test_list_tipologias_returns_all():
    result = await public.list_tipologias()
    assert "typologies" in result
    assert "total" in result
    assert result["total"] >= 22  # at least T01-T22
    assert len(result["typologies"]) == result["total"]


@pytest.mark.asyncio
async def test_list_tipologias_items_have_required_fields():
    result = await public.list_tipologias()
    for item in result["typologies"]:
        assert "code" in item, f"missing 'code' in {item}"
        assert "name" in item, f"missing 'name' in {item}"
        assert "corruption_types" in item
        assert "law_articles" in item
        assert isinstance(item["code"], str)
        assert item["code"].startswith("T")


@pytest.mark.asyncio
async def test_list_tipologias_contains_t03():
    result = await public.list_tipologias()
    codes = {item["code"] for item in result["typologies"]}
    assert "T03" in codes


@pytest.mark.asyncio
async def test_get_tipologia_known_code():
    result = await public.get_tipologia("T03")
    assert result["code"] == "T03"
    assert isinstance(result["name"], str)
    assert len(result["name"]) > 0
    assert isinstance(result["law_articles"], list)


@pytest.mark.asyncio
async def test_get_tipologia_case_insensitive():
    result = await public.get_tipologia("t03")
    assert result["code"] == "T03"


@pytest.mark.asyncio
async def test_get_tipologia_unknown_raises_404():
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        await public.get_tipologia("T99")
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_list_tipologias_no_duplicate_codes():
    result = await public.list_tipologias()
    codes = [item["code"] for item in result["typologies"]]
    assert len(codes) == len(set(codes)), "duplicate typology codes in list"
