"""Tests for GET /internal/data-quality endpoint."""
from unittest.mock import AsyncMock, patch

from api.app.routers import internal


async def test_data_quality_returns_expected_keys(monkeypatch):
    """Endpoint delegates to get_data_quality_dashboard and returns its result."""
    expected = {
        "sources": [
            {
                "connector": "portal_transparencia",
                "job": "contratos",
                "total_items": 5000,
                "freshness_lag_hours": 12.0,
                "last_success_at": "2026-03-03T10:00:00+00:00",
                "veracity_score": 0.95,
                "status": "ok",
            }
        ],
        "cross_source_overlap": [
            {"source_count": 1, "entity_count": 3200},
            {"source_count": 2, "entity_count": 450},
        ],
        "alerts": [],
    }

    mock_dashboard = AsyncMock(return_value=expected)

    with patch.object(internal, "get_data_quality_dashboard", mock_dashboard):
        # Patch async_session context manager
        mock_session = AsyncMock()
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("api.app.routers.internal.async_session", return_value=mock_ctx):
            result = await internal.data_quality()

    assert result == expected
    assert "sources" in result
    assert "cross_source_overlap" in result
    assert "alerts" in result
    mock_dashboard.assert_awaited_once_with(mock_session)


async def test_data_quality_alerts_flagged(monkeypatch):
    """Alert entries have required fields."""
    expected = {
        "sources": [],
        "cross_source_overlap": [],
        "alerts": [
            {"connector": "camara", "job": "despesas", "alert": "weekly_drop", "drop_pct": 35.5}
        ],
    }

    mock_dashboard = AsyncMock(return_value=expected)

    with patch.object(internal, "get_data_quality_dashboard", mock_dashboard):
        mock_session = AsyncMock()
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("api.app.routers.internal.async_session", return_value=mock_ctx):
            result = await internal.data_quality()

    assert len(result["alerts"]) == 1
    alert = result["alerts"][0]
    assert alert["alert"] == "weekly_drop"
    assert alert["drop_pct"] > 20.0
