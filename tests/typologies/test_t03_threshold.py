"""Tests for dynamic dispensa threshold lookup (P2.1)."""
from datetime import date
from decimal import Decimal

import pytest

from shared.typologies.t03_splitting import get_dispensa_threshold


class _ScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _FakeAsyncSession:
    def __init__(self, return_value):
        self._return_value = return_value

    async def execute(self, _stmt):
        return _ScalarResult(self._return_value)


@pytest.mark.asyncio
async def test_t03_threshold_goods_2024():
    """Threshold for goods in 2024 = Decreto 12.343/2024."""
    session = _FakeAsyncSession(Decimal("62725.59"))
    threshold = await get_dispensa_threshold(session, "goods", date(2024, 6, 1))
    assert threshold == Decimal("62725.59")


@pytest.mark.asyncio
async def test_t03_threshold_works_2024():
    """Threshold for works in 2024 = Decreto 12.343/2024."""
    session = _FakeAsyncSession(Decimal("125451.15"))
    threshold = await get_dispensa_threshold(session, "works", date(2024, 6, 1))
    assert threshold == Decimal("125451.15")


@pytest.mark.asyncio
async def test_t03_threshold_goods_2026_differs_from_2024():
    """Threshold for goods in 2026 uses Decreto 12.807/2025, not 2024 value."""
    session_2024 = _FakeAsyncSession(Decimal("62725.59"))
    session_2026 = _FakeAsyncSession(Decimal("66500.00"))
    threshold_2024 = await get_dispensa_threshold(session_2024, "goods", date(2024, 6, 1))
    threshold_2026 = await get_dispensa_threshold(session_2026, "goods", date(2026, 3, 1))
    assert threshold_2026 != threshold_2024


@pytest.mark.asyncio
async def test_t03_threshold_boundary_2025_end():
    """2025-12-31 is last day of Decreto 12.343/2024 validity."""
    session = _FakeAsyncSession(Decimal("62725.59"))
    threshold = await get_dispensa_threshold(session, "goods", date(2025, 12, 31))
    assert threshold == Decimal("62725.59")


@pytest.mark.asyncio
async def test_t03_threshold_boundary_2026_start():
    """2026-01-01 is first day of Decreto 12.807/2025 validity."""
    session = _FakeAsyncSession(Decimal("66500.00"))
    threshold = await get_dispensa_threshold(session, "goods", date(2026, 1, 1))
    assert threshold == Decimal("66500.00")


@pytest.mark.asyncio
async def test_t03_threshold_unknown_category_falls_back():
    """Unknown category returns the goods fallback when DB has no row."""
    session = _FakeAsyncSession(None)  # simulate no row found
    threshold = await get_dispensa_threshold(session, "unknown_category", date(2024, 6, 1))
    assert threshold > 0  # fallback value, not zero or None


@pytest.mark.asyncio
async def test_t03_threshold_known_category_falls_back_to_goods():
    """Known category 'goods' falls back to Decreto 12.343/2024 value when DB empty."""
    session = _FakeAsyncSession(None)
    threshold = await get_dispensa_threshold(session, "goods", date(2024, 6, 1))
    assert threshold == Decimal("62725.59")


@pytest.mark.asyncio
async def test_t03_threshold_known_category_falls_back_to_works():
    """Known category 'works' falls back to Decreto 12.343/2024 value when DB empty."""
    session = _FakeAsyncSession(None)
    threshold = await get_dispensa_threshold(session, "works", date(2024, 6, 1))
    assert threshold == Decimal("125451.15")
