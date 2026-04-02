import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from openwatch_queries import queries


class _ExecResult:
    def __init__(self, *, scalar_values=None):
        self._scalar_values = scalar_values or []

    def scalars(self):
        return self

    def all(self):
        return self._scalar_values


@pytest.mark.asyncio
async def test_get_signal_evidence_page_occurred_at_desc_keeps_nulls_last(monkeypatch):
    signal_id = uuid.uuid4()
    event_a = uuid.uuid4()
    event_b = uuid.uuid4()
    event_c = uuid.uuid4()

    signal = SimpleNamespace(
        id=signal_id,
        typology=SimpleNamespace(code="T03"),
        event_ids=[str(event_a), str(event_b), str(event_c)],
        evidence_refs=[],
    )

    async def _fake_get_signal_by_id(_session, _signal_id):
        return signal

    monkeypatch.setattr(queries, "get_signal_by_id", _fake_get_signal_by_id)

    class _FakeSession:
        async def execute(self, _stmt):
            rows = [
                SimpleNamespace(
                    id=event_a,
                    occurred_at=datetime(2026, 3, 1, 20, 0, tzinfo=timezone.utc),
                    value_brl=100.0,
                    description="A",
                    source_connector="compras_gov",
                    source_id="a",
                    subtype="dispensa",
                    attrs={"catmat_group": "unknown", "modality": "Dispensa"},
                ),
                SimpleNamespace(
                    id=event_b,
                    occurred_at=None,
                    value_brl=200.0,
                    description="B",
                    source_connector="compras_gov",
                    source_id="b",
                    subtype="dispensa",
                    attrs={"catmat_group": "2", "modality": "Dispensa"},
                ),
                SimpleNamespace(
                    id=event_c,
                    occurred_at=datetime(2026, 3, 1, 21, 0, tzinfo=timezone.utc),
                    value_brl=300.0,
                    description="C",
                    source_connector="compras_gov",
                    source_id="c",
                    subtype="dispensa",
                    attrs={"catmat_group": "3", "modality": "Dispensa"},
                ),
            ]
            return _ExecResult(scalar_values=rows)

    page = await queries.get_signal_evidence_page(
        _FakeSession(),
        signal_id=signal_id,
        offset=0,
        limit=10,
        sort="occurred_at_desc",
    )

    assert page is not None
    assert [item["event_id"] for item in page["items"]] == [str(event_c), str(event_a), str(event_b)]
    assert page["items"][0]["evidence_reason"] == "Compoe o cluster temporal e o somatorio do sinal"
    assert page["items"][0]["catmat_group"] == "3"
    assert page["items"][1]["catmat_group"] == "nao_informado"
