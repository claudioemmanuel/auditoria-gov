import uuid
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException

from api.app.routers import public


@pytest.mark.asyncio
async def test_coverage_v2_summary_endpoint_returns_payload(monkeypatch):
    async def _fake_get_coverage_v2_summary(*_args, **_kwargs):
        return {
            "snapshot_at": datetime.now(timezone.utc),
            "totals": {
                "connectors": 10,
                "jobs": 30,
                "jobs_enabled": 26,
                "signals_total": 12,
                "status_counts": {"ok": 10, "warning": 2, "stale": 1, "error": 0, "pending": 17},
                "runtime": {"running": 1, "stuck": 0, "failed_or_stuck": 0},
            },
            "pipeline": {"overall_status": "attention", "stages": []},
            "schedule_windows_brt": [{"job_code": "ingest-all-incremental", "window": "a cada 2h"}],
        }

    monkeypatch.setattr(public, "get_coverage_v2_summary", _fake_get_coverage_v2_summary)

    payload = await public.coverage_v2_summary(session=None)
    assert payload["totals"]["jobs"] == 30


@pytest.mark.asyncio
async def test_coverage_v2_sources_endpoint_returns_paginated_payload(monkeypatch):
    async def _fake_get_coverage_v2_sources(*_args, **_kwargs):
        return {
            "items": [{"connector": "portal_transparencia", "job_count": 8, "worst_status": "warning"}],
            "total": 1,
            "offset": 0,
            "limit": 20,
        }

    monkeypatch.setattr(public, "get_coverage_v2_sources", _fake_get_coverage_v2_sources)

    payload = await public.coverage_v2_sources(session=None, pagination=public.Pagination())
    assert payload["total"] == 1
    assert payload["items"][0]["connector"] == "portal_transparencia"


@pytest.mark.asyncio
async def test_coverage_v2_map_endpoint_returns_payload(monkeypatch):
    async def _fake_get_coverage_v2_map(*_args, **_kwargs):
        return {
            "layer": "uf",
            "metric": "coverage",
            "generated_at": datetime.now(timezone.utc),
            "date_ref": datetime.now(timezone.utc),
            "national": {
                "regions_with_data": 1,
                "regions_without_data": 26,
                "total_events": 10,
                "total_signals": 3,
            },
            "items": [],
        }

    monkeypatch.setattr(public, "get_coverage_v2_map", _fake_get_coverage_v2_map)

    payload = await public.coverage_v2_map(session=None)
    assert payload["national"]["total_events"] == 10


@pytest.mark.asyncio
async def test_coverage_v2_analytics_endpoint_returns_payload(monkeypatch):
    async def _fake_get_coverage_v2_analytics(*_args, **_kwargs):
        return {
            "summary": {"total_typologies": 1, "apt_count": 1, "blocked_count": 0, "with_signals_30d": 1},
            "items": [],
        }

    monkeypatch.setattr(public, "get_coverage_v2_analytics", _fake_get_coverage_v2_analytics)

    payload = await public.coverage_v2_analytics(session=None)
    assert payload["summary"]["apt_count"] == 1


@pytest.mark.asyncio
async def test_coverage_v2_source_preview_404(monkeypatch):
    async def _fake_get_coverage_v2_source_preview(*_args, **_kwargs):
        return None

    monkeypatch.setattr(public, "get_coverage_v2_source_preview", _fake_get_coverage_v2_source_preview)

    with pytest.raises(HTTPException) as exc:
        await public.coverage_v2_source_preview(connector="inexistente", session=None)

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_coverage_v2_run_detail_404(monkeypatch):
    async def _fake_get_coverage_v2_run_detail(*_args, **_kwargs):
        return None

    monkeypatch.setattr(public, "get_coverage_v2_run_detail", _fake_get_coverage_v2_run_detail)

    with pytest.raises(HTTPException) as exc:
        await public.coverage_v2_run_detail(run_id=uuid.uuid4(), session=None)

    assert exc.value.status_code == 404
