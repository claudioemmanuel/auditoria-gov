import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

from api.app.routers import public


async def test_case_detail_enriches_associated_signals(monkeypatch):
    case_id = uuid.uuid4()
    signal_id = uuid.uuid4()

    signal = SimpleNamespace(
        id=signal_id,
        typology=SimpleNamespace(code="T03", name="Fracionamento de Despesa"),
        severity="high",
        confidence=0.87,
        title="Possível fracionamento",
        summary="Resumo do sinal",
        explanation_md=None,
        factors={
            "n_purchases": 4,
            "total_value_brl": 200000.0,
            "ratio": 4.0,
        },
        created_at=datetime(2026, 3, 2, 11, 0, tzinfo=timezone.utc),
        event_ids=[str(uuid.uuid4()), str(uuid.uuid4())],
        entity_ids=[str(uuid.uuid4())],
        period_start=datetime(2026, 3, 1, 10, 0, tzinfo=timezone.utc),
        period_end=datetime(2026, 3, 1, 12, 0, tzinfo=timezone.utc),
    )
    case = SimpleNamespace(
        id=case_id,
        title="Caso X",
        status="open",
        severity="high",
        summary="2 sinais agrupados por entidade",
        attrs={
            "entity_names": ["Prefeitura A"],
            "total_value_brl": 200000.0,
            "period_start": "2026-03-01T10:00:00+00:00",
            "period_end": "2026-03-01T12:00:00+00:00",
        },
        created_at=datetime(2026, 3, 2, 11, 0, tzinfo=timezone.utc),
        items=[SimpleNamespace(signal=signal)],
    )

    async def _fake_get_case_by_id(_session, _case_id):
        return case

    monkeypatch.setattr(public, "get_case_by_id", _fake_get_case_by_id)

    result = await public.case_detail(case_id=case_id, session=None)

    assert result["id"] == case_id
    assert result["typology_names"] == ["Fracionamento de Despesa"]
    assert len(result["signals"]) == 1
    first_signal = result["signals"][0]
    assert first_signal["id"] == signal_id
    assert first_signal["evidence_count"] == 2
    assert first_signal["entity_count"] == 1
    assert first_signal["period_start"] == signal.period_start
    assert first_signal["period_end"] == signal.period_end
    assert "n_purchases" in first_signal["factor_descriptions"]
