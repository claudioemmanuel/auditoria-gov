import uuid

from api.app.routers import public


async def test_signal_evidence_endpoint_returns_paginated_payload(monkeypatch):
    signal_id = uuid.uuid4()

    async def _fake_get_signal_evidence_page(*_args, **_kwargs):
        return {
            "signal_id": str(signal_id),
            "total": 70,
            "offset": 0,
            "limit": 10,
            "items": [
                {
                    "event_id": str(uuid.uuid4()),
                    "occurred_at": "2026-03-01T19:26:29+00:00",
                    "value_brl": 15750.0,
                    "description": "Compra X",
                    "source_connector": "compras_gov",
                    "source_id": "abc",
                    "modality": "Dispensa",
                    "catmat_group": "nao_informado",
                    "evidence_reason": "Compõe o cluster temporal e o somatório do sinal",
                }
            ],
        }

    monkeypatch.setattr(public, "get_signal_evidence_page", _fake_get_signal_evidence_page)

    result = await public.signal_evidence(signal_id=signal_id, session=None, pagination=public.Pagination())

    assert result["signal_id"] == str(signal_id)
    assert result["total"] == 70
    assert result["limit"] == 10
    assert len(result["items"]) == 1
