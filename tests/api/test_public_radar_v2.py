import uuid
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException

from api.app.routers import public


@pytest.mark.asyncio
async def test_radar_v2_summary_endpoint_returns_payload(monkeypatch):
    async def _fake_get_radar_v2_summary(*_args, **_kwargs):
        return {
            "snapshot_at": datetime.now(timezone.utc),
            "totals": {"signals": 5, "cases": 2},
            "severity_counts": {"low": 0, "medium": 1, "high": 2, "critical": 2},
            "typology_counts": [{"code": "T03", "name": "Fracionamento de Despesa", "count": 5}],
            "active_filters_count": 1,
        }

    monkeypatch.setattr(public, "get_radar_v2_summary", _fake_get_radar_v2_summary)

    result = await public.radar_v2_summary(session=None, typology="T03")
    assert result["totals"]["signals"] == 5
    assert result["typology_counts"][0]["code"] == "T03"


@pytest.mark.asyncio
async def test_radar_v2_signals_endpoint_returns_paginated_payload(monkeypatch):
    async def _fake_get_radar_v2_signals(*_args, **_kwargs):
        return (
            [
                {
                    "id": str(uuid.uuid4()),
                    "typology_code": "T03",
                    "typology_name": "Fracionamento de Despesa",
                    "severity": "high",
                    "confidence": 0.83,
                    "title": "Possivel fracionamento",
                    "summary": "Resumo",
                    "period_start": None,
                    "period_end": None,
                    "created_at": datetime.now(timezone.utc),
                    "event_count": 7,
                    "entity_count": 1,
                    "has_graph": True,
                }
            ],
            1,
        )

    monkeypatch.setattr(public, "get_radar_v2_signals", _fake_get_radar_v2_signals)

    result = await public.radar_v2_signals(
        session=None,
        pagination=public.Pagination(),
    )

    assert result["total"] == 1
    assert result["items"][0]["event_count"] == 7


@pytest.mark.asyncio
async def test_radar_v2_signal_preview_endpoint_404(monkeypatch):
    async def _fake_get_radar_v2_signal_preview(*_args, **_kwargs):
        return None

    monkeypatch.setattr(public, "get_radar_v2_signal_preview", _fake_get_radar_v2_signal_preview)

    with pytest.raises(HTTPException) as exc:
        await public.radar_v2_signal_preview(signal_id=uuid.uuid4(), session=None)

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_radar_v2_coverage_endpoint(monkeypatch):
    async def _fake_get_radar_v2_coverage(*_args, **_kwargs):
        return {"summary": {"apt_count": 1, "with_signals_30d": 1, "blocked_count": 0, "total_typologies": 1}, "items": []}

    monkeypatch.setattr(public, "get_radar_v2_coverage", _fake_get_radar_v2_coverage)

    result = await public.radar_v2_coverage(session=None)
    assert result["summary"]["apt_count"] == 1
