"""Tests for LLM guardrail decorator (@explanatory_only)."""

import pytest

from openwatch_ai.provider import explanatory_only


@explanatory_only
async def _returns_string():
    return "This is an explanation."


@explanatory_only
async def _returns_number():
    return 42


@explanatory_only
async def _returns_dict():
    return {"score": 0.95, "label": "high"}


@explanatory_only
async def _returns_none():
    return None


class TestExplanatoryOnly:
    @pytest.mark.asyncio
    async def test_allows_string_return(self):
        result = await _returns_string()
        assert result == "This is an explanation."

    @pytest.mark.asyncio
    async def test_rejects_numeric_return(self):
        with pytest.raises(TypeError, match="must return str"):
            await _returns_number()

    @pytest.mark.asyncio
    async def test_rejects_dict_return(self):
        with pytest.raises(TypeError, match="must return str"):
            await _returns_dict()

    @pytest.mark.asyncio
    async def test_rejects_none_return(self):
        with pytest.raises(TypeError, match="must return str"):
            await _returns_none()
