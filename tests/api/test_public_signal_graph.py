import uuid

import pytest
from fastapi import HTTPException

from api.app.routers import public
from shared.models.graph import CaseGraphResponse


@pytest.mark.asyncio
async def test_signal_graph_endpoint_returns_payload(monkeypatch):
    signal_id = uuid.uuid4()

    async def _fake_get_signal_graph(*_args, **_kwargs):
        return {
            "signal": {
                "id": str(signal_id),
                "typology_code": "T03",
                "typology_name": "Fracionamento de Despesa",
                "severity": "high",
                "confidence": 0.91,
                "title": "Possivel fracionamento",
                "period_start": None,
                "period_end": None,
            },
            "pattern_story": {
                "pattern_label": "Fracionamento de Despesa",
                "started_at": None,
                "ended_at": None,
                "started_from_entities": [],
                "flow_targets": [],
                "why_flagged": "Padrao identificado",
            },
            "overview": {"nodes": [], "edges": []},
            "timeline": [],
            "involved_entities": [],
            "diagnostics": {"events_total": 0, "events_loaded": 0, "participants_total": 0},
        }

    monkeypatch.setattr(public, "get_signal_graph", _fake_get_signal_graph)

    response = await public.signal_graph(signal_id=signal_id, session=None)

    assert response["signal"]["id"] == str(signal_id)
    assert response["signal"]["typology_code"] == "T03"


@pytest.mark.asyncio
async def test_signal_graph_endpoint_returns_404_when_missing(monkeypatch):
    signal_id = uuid.uuid4()

    async def _fake_get_signal_graph(*_args, **_kwargs):
        return None

    monkeypatch.setattr(public, "get_signal_graph", _fake_get_signal_graph)

    with pytest.raises(HTTPException) as exc:
        await public.signal_graph(signal_id=signal_id, session=None)

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_case_graph_passes_focus_signal_id(monkeypatch):
    case_id = uuid.uuid4()
    focus_signal_id = uuid.uuid4()
    captured = {}

    async def _fake_get_case_graph(_session, _case_id, depth=1, limit=300, focus_signal_id=None):
        captured["case_id"] = _case_id
        captured["depth"] = depth
        captured["focus_signal_id"] = focus_signal_id
        return CaseGraphResponse(
            case_id=_case_id,
            case_title="Caso teste",
            case_severity="high",
            case_status="open",
            seed_entity_ids=[],
            nodes=[],
            edges=[],
            signals=[],
            truncated=False,
        )

    monkeypatch.setattr(public, "get_case_graph", _fake_get_case_graph)

    result = await public.case_graph(
        case_id=case_id,
        session=None,
        depth=2,
        focus_signal_id=focus_signal_id,
    )

    assert result.case_id == case_id
    assert captured["case_id"] == case_id
    assert captured["depth"] == 2
    assert captured["focus_signal_id"] == focus_signal_id
