import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from shared.repo import queries


class _ExecResult:
    def __init__(self, *, scalar_values=None, rows=None):
        self._scalar_values = scalar_values or []
        self._rows = rows or []

    def scalars(self):
        return self

    def all(self):
        return self._scalar_values

    def __iter__(self):
        return iter(self._rows)


@pytest.mark.asyncio
async def test_get_signal_graph_orders_timeline_and_sets_story_bounds(monkeypatch):
    signal_id = uuid.uuid4()
    org_id = uuid.uuid4()
    supplier_id = uuid.uuid4()
    event_early = uuid.uuid4()
    event_late = uuid.uuid4()

    early_at = datetime(2026, 3, 1, 10, 0, tzinfo=timezone.utc)
    late_at = datetime(2026, 3, 1, 18, 0, tzinfo=timezone.utc)

    signal = SimpleNamespace(
        id=signal_id,
        typology=SimpleNamespace(code="T03", name="Fracionamento de Despesa"),
        severity="high",
        confidence=0.91,
        title="Possivel fracionamento",
        summary="Cluster temporal suspeito",
        factors={
            "n_purchases": 2,
            "total_value_brl": 90000.0,
            "threshold_brl": 50000.0,
            "ratio": 1.8,
        },
        period_start=early_at,
        period_end=late_at,
        event_ids=[str(event_late), str(event_early)],
        entity_ids=[str(org_id), str(supplier_id)],
    )

    async def _fake_get_signal_by_id(_session, _signal_id):
        return signal

    monkeypatch.setattr(queries, "get_signal_by_id", _fake_get_signal_by_id)

    org_entity = SimpleNamespace(
        id=org_id,
        name="Prefeitura Municipal X",
        type="org",
        identifiers={"cnpj": "00000000000191"},
        attrs={"url_foto": "https://example.org/prefeitura.png", "uf": "MG"},
    )
    supplier_entity = SimpleNamespace(
        id=supplier_id,
        name="Fornecedor Y",
        type="company",
        identifiers={"cnpj": "11111111000191"},
        attrs={},
    )

    class _FakeSession:
        def __init__(self):
            self._calls = 0

        async def execute(self, _stmt):
            self._calls += 1
            if self._calls == 1:
                return _ExecResult(
                    scalar_values=[
                        SimpleNamespace(
                            id=event_late,
                            occurred_at=late_at,
                            value_brl=30000.0,
                            description="Compra 2",
                            source_connector="compras_gov",
                            source_id="evt-2",
                            subtype="dispensa",
                            attrs={"modality": "Dispensa", "catmat_group": "insumo"},
                        ),
                        SimpleNamespace(
                            id=event_early,
                            occurred_at=early_at,
                            value_brl=60000.0,
                            description="Compra 1",
                            source_connector="compras_gov",
                            source_id="evt-1",
                            subtype="dispensa",
                            attrs={"modality": "Dispensa", "catmat_group": "insumo"},
                        ),
                    ]
                )
            if self._calls == 2:
                rows = [
                    (
                        SimpleNamespace(
                            event_id=event_early,
                            entity_id=org_id,
                            role="buyer",
                            attrs={},
                        ),
                        org_entity,
                    ),
                    (
                        SimpleNamespace(
                            event_id=event_early,
                            entity_id=supplier_id,
                            role="supplier",
                            attrs={},
                        ),
                        supplier_entity,
                    ),
                    (
                        SimpleNamespace(
                            event_id=event_late,
                            entity_id=org_id,
                            role="buyer",
                            attrs={},
                        ),
                        org_entity,
                    ),
                    (
                        SimpleNamespace(
                            event_id=event_late,
                            entity_id=supplier_id,
                            role="supplier",
                            attrs={},
                        ),
                        supplier_entity,
                    ),
                ]
                return _ExecResult(rows=rows)
            raise AssertionError(f"Unexpected execute call {self._calls}")

    graph = await queries.get_signal_graph(_FakeSession(), signal_id)

    assert graph is not None
    assert graph.pattern_story.started_at == early_at
    assert graph.pattern_story.ended_at == late_at
    assert [str(item.event_id) for item in graph.timeline] == [str(event_early), str(event_late)]
    assert graph.diagnostics.events_total == 2
    assert graph.diagnostics.events_loaded == 2
    assert graph.overview.edges
    assert any(
        entity.photo_url == "https://example.org/prefeitura.png"
        for entity in graph.involved_entities
    )
