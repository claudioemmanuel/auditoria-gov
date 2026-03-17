import uuid
from collections import defaultdict
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from shared.repo import queries


class _ExecResult:
    def __init__(self, *, scalar=None, scalar_values=None, rows=None):
        self._scalar = scalar
        self._scalar_values = scalar_values or []
        self._rows = rows or []

    def scalar_one_or_none(self):
        return self._scalar

    def scalars(self):
        return self

    def all(self):
        if self._rows:
            return self._rows
        return self._scalar_values


def _make_case(case_id, *, entity_names=None, attrs=None):
    return SimpleNamespace(
        id=case_id,
        title="Caso Teste",
        severity="high",
        status="open",
        summary="Resumo do caso",
        case_type="compound",
        attrs=attrs or {"entity_names": entity_names or []},
        created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )


def _make_signal_row(
    signal_id,
    typology_code="T03",
    typology_name="Fracionamento de Despesa",
    severity="critical",
    confidence=0.91,
    event_ids=None,
    entity_ids=None,
    factors=None,
    period_start=None,
    period_end=None,
):
    return SimpleNamespace(
        id=signal_id,
        typology_id=uuid.uuid4(),
        typology_code=typology_code,
        typology_name=typology_name,
        severity=severity,
        confidence=confidence,
        title=f"Sinal {typology_code}",
        summary=f"Resumo {typology_code}",
        entity_ids=entity_ids or [],
        event_ids=event_ids or [],
        factors=factors or {},
        period_start=period_start,
        period_end=period_end,
    )


def _make_event(event_id, *, occurred_at=None, value_brl=None, source_connector="pncp"):
    return SimpleNamespace(
        id=event_id,
        type="licitacao",
        subtype=None,
        description="Compra direta",
        occurred_at=occurred_at or datetime(2025, 3, 1, tzinfo=timezone.utc),
        source_connector=source_connector,
        source_id="src-1",
        value_brl=value_brl or 1000.0,
        attrs={"modality": "dispensa"},
    )


def _make_participant(event_id, entity_id, role="buyer"):
    return SimpleNamespace(
        event_id=event_id,
        entity_id=entity_id,
        role=role,
        attrs={},
    )


def _make_entity(entity_id, name="Empresa X", entity_type="company"):
    return SimpleNamespace(
        id=entity_id,
        type=entity_type,
        name=name,
        identifiers={"cnpj": "12345678000199"},
        attrs={},
    )


def _make_legal_hypothesis(law_name="Lei 14.133/2021", article="Art. 9", violation_type="fraude"):
    return SimpleNamespace(
        law_name=law_name,
        article=article,
        violation_type=violation_type,
        confidence=0.8,
    )


@pytest.mark.asyncio
async def test_get_dossier_timeline_not_found():
    """Returns None for non-existent case."""
    class _FakeSession:
        async def execute(self, stmt, params=None):
            return _ExecResult(scalar=None)

    result = await queries.get_dossier_timeline(_FakeSession(), uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_get_dossier_timeline_full_response():
    """Returns full timeline with case, events, signals, entities, legal, related."""
    case_id = uuid.uuid4()
    signal_id = uuid.uuid4()
    event_id = uuid.uuid4()
    entity_id_buyer = uuid.uuid4()
    entity_id_supplier = uuid.uuid4()

    case = _make_case(case_id, entity_names=["Empresa X"])

    signal_row = _make_signal_row(
        signal_id,
        event_ids=[str(event_id)],
        entity_ids=[str(entity_id_buyer), str(entity_id_supplier)],
        factors={"total_value_brl": 50000.0},
        period_start=datetime(2025, 1, 1, tzinfo=timezone.utc),
        period_end=datetime(2025, 6, 1, tzinfo=timezone.utc),
    )

    event = _make_event(event_id)
    participant_buyer = _make_participant(event_id, entity_id_buyer, "buyer")
    participant_supplier = _make_participant(event_id, entity_id_supplier, "supplier")
    entity_buyer = _make_entity(entity_id_buyer, "Prefeitura de Andradas", "org")
    entity_supplier = _make_entity(entity_id_supplier, "Empresa X", "company")
    legal = _make_legal_hypothesis()
    related = SimpleNamespace(id=uuid.uuid4(), title="Caso Relacionado", severity="medium")

    call_count = 0

    class _FakeSession:
        async def execute(self, stmt, params=None):
            nonlocal call_count
            call_count += 1

            # 1: case lookup
            if call_count == 1:
                return _ExecResult(scalar=case)
            # 2: signals join
            if call_count == 2:
                return _ExecResult(rows=[signal_row])
            # 3: legal hypotheses
            if call_count == 3:
                return _ExecResult(scalar_values=[legal])
            # 4: related cases (text query)
            if call_count == 4:
                return _ExecResult(rows=[related])

            raise AssertionError(f"Unexpected call {call_count}")

    chunked_calls = []

    async def _ordered_chunked_in(_session, stmt_factory, ids, **kwargs):
        chunked_calls.append(list(ids))
        call_idx = len(chunked_calls)
        if call_idx == 1:
            # events
            return [event]
        if call_idx == 2:
            # participants
            return [participant_buyer, participant_supplier]
        if call_idx == 3:
            # entities
            return [entity_buyer, entity_supplier]
        return []

    with patch("shared.utils.query.execute_chunked_in", side_effect=_ordered_chunked_in):
        result = await queries.get_dossier_timeline(_FakeSession(), case_id)

    assert result is not None

    # Case
    assert result["case"]["id"] == str(case_id)
    assert result["case"]["title"] == "Caso Teste"
    assert result["case"]["severity"] == "high"
    assert result["case"]["status"] == "open"
    assert result["case"]["case_type"] == "compound"

    # Signals
    assert len(result["signals"]) == 1
    sig = result["signals"][0]
    assert sig["id"] == str(signal_id)
    assert sig["typology_code"] == "T03"
    assert sig["confidence"] == 0.91
    assert sig["factors"] == {"total_value_brl": 50000.0}
    assert sig["period_start"] == "2025-01-01T00:00:00+00:00"
    assert sig["period_end"] == "2025-06-01T00:00:00+00:00"
    assert sig["entity_count"] == 2
    assert sig["event_count"] == 1
    assert "factor_descriptions" in sig

    # Events
    assert len(result["events"]) == 1
    ev = result["events"][0]
    assert ev["id"] == str(event_id)
    assert ev["type"] == "licitacao"
    assert ev["value_brl"] == 1000.0
    assert ev["source_connector"] == "pncp"
    assert len(ev["participants"]) == 2
    roles = {p["role"] for p in ev["participants"]}
    assert "buyer" in roles
    assert "supplier" in roles
    # Check role_label
    buyer_p = next(p for p in ev["participants"] if p["role"] == "buyer")
    assert buyer_p["role_label"] == "Orgao comprador"
    supplier_p = next(p for p in ev["participants"] if p["role"] == "supplier")
    assert supplier_p["role_label"] == "Fornecedor"
    # Check signals linked to event
    assert len(ev["signals"]) == 1
    assert ev["signals"][0]["id"] == str(signal_id)

    # Entities
    assert len(result["entities"]) == 2
    entity_ids_out = {e["id"] for e in result["entities"]}
    assert str(entity_id_buyer) in entity_ids_out
    assert str(entity_id_supplier) in entity_ids_out
    # Full identifiers (no masking)
    for e in result["entities"]:
        assert "identifiers" in e
        assert e["identifiers"].get("cnpj") == "12345678000199"

    # Legal hypotheses
    assert len(result["legal_hypotheses"]) == 1
    assert result["legal_hypotheses"][0]["law"] == "Lei 14.133/2021"
    assert result["legal_hypotheses"][0]["article"] == "Art. 9"

    # Related cases
    assert len(result["related_cases"]) == 1
    assert result["related_cases"][0]["title"] == "Caso Relacionado"


@pytest.mark.asyncio
async def test_get_dossier_timeline_empty_signals():
    """Case with no signals returns empty events/signals/entities."""
    case_id = uuid.uuid4()
    case = _make_case(case_id)

    call_count = 0

    class _FakeSession:
        async def execute(self, stmt, params=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _ExecResult(scalar=case)
            if call_count == 2:
                return _ExecResult(rows=[])  # no signals
            if call_count == 3:
                return _ExecResult(scalar_values=[])  # no legal
            if call_count == 4:
                return _ExecResult(rows=[])  # no related
            raise AssertionError(f"Unexpected call {call_count}")

    with patch("shared.utils.query.execute_chunked_in", new_callable=AsyncMock, return_value=[]):
        result = await queries.get_dossier_timeline(_FakeSession(), case_id)

    assert result is not None
    assert result["case"]["id"] == str(case_id)
    assert result["events"] == []
    assert result["signals"] == []
    assert result["entities"] == []
    assert result["legal_hypotheses"] == []
    assert result["related_cases"] == []


@pytest.mark.asyncio
async def test_get_dossier_timeline_events_sorted_by_occurred_at():
    """Events are sorted by occurred_at ascending."""
    case_id = uuid.uuid4()
    signal_id = uuid.uuid4()
    event_id_1 = uuid.uuid4()
    event_id_2 = uuid.uuid4()
    entity_id = uuid.uuid4()

    case = _make_case(case_id)

    signal_row = _make_signal_row(
        signal_id,
        event_ids=[str(event_id_1), str(event_id_2)],
        entity_ids=[str(entity_id)],
    )

    event_late = _make_event(event_id_1, occurred_at=datetime(2025, 6, 1, tzinfo=timezone.utc))
    event_early = _make_event(event_id_2, occurred_at=datetime(2025, 1, 1, tzinfo=timezone.utc))
    entity = _make_entity(entity_id)

    call_count = 0

    class _FakeSession:
        async def execute(self, stmt, params=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _ExecResult(scalar=case)
            if call_count == 2:
                return _ExecResult(rows=[signal_row])
            if call_count == 3:
                return _ExecResult(scalar_values=[])
            if call_count == 4:
                return _ExecResult(rows=[])
            raise AssertionError(f"Unexpected call {call_count}")

    chunked_calls = []

    async def _ordered_chunked_in(_session, stmt_factory, ids, **kwargs):
        chunked_calls.append(list(ids))
        call_idx = len(chunked_calls)
        if call_idx == 1:
            return [event_late, event_early]
        if call_idx == 2:
            return []  # no participants
        if call_idx == 3:
            return [entity]
        return []

    with patch("shared.utils.query.execute_chunked_in", side_effect=_ordered_chunked_in):
        result = await queries.get_dossier_timeline(_FakeSession(), case_id)

    assert len(result["events"]) == 2
    assert result["events"][0]["id"] == str(event_id_2)  # early first
    assert result["events"][1]["id"] == str(event_id_1)  # late second


@pytest.mark.asyncio
async def test_get_dossier_timeline_participant_entities_included():
    """Entities referenced only by participants (not in signal.entity_ids) are included."""
    case_id = uuid.uuid4()
    signal_id = uuid.uuid4()
    event_id = uuid.uuid4()
    entity_in_signal = uuid.uuid4()
    entity_only_participant = uuid.uuid4()

    case = _make_case(case_id)

    signal_row = _make_signal_row(
        signal_id,
        event_ids=[str(event_id)],
        entity_ids=[str(entity_in_signal)],
    )

    event = _make_event(event_id)
    participant = _make_participant(event_id, entity_only_participant, "supplier")
    entity_a = _make_entity(entity_in_signal, "Entidade A")
    entity_b = _make_entity(entity_only_participant, "Entidade B")

    call_count = 0

    class _FakeSession:
        async def execute(self, stmt, params=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _ExecResult(scalar=case)
            if call_count == 2:
                return _ExecResult(rows=[signal_row])
            if call_count == 3:
                return _ExecResult(scalar_values=[])
            if call_count == 4:
                return _ExecResult(rows=[])
            raise AssertionError(f"Unexpected call {call_count}")

    chunked_calls = []

    async def _ordered_chunked_in(_session, stmt_factory, ids, **kwargs):
        chunked_calls.append(list(ids))
        call_idx = len(chunked_calls)
        if call_idx == 1:
            return [event]
        if call_idx == 2:
            return [participant]
        if call_idx == 3:
            return [entity_a, entity_b]
        return []

    with patch("shared.utils.query.execute_chunked_in", side_effect=_ordered_chunked_in):
        result = await queries.get_dossier_timeline(_FakeSession(), case_id)

    entity_ids_out = {e["id"] for e in result["entities"]}
    assert str(entity_in_signal) in entity_ids_out
    assert str(entity_only_participant) in entity_ids_out


@pytest.mark.asyncio
async def test_get_dossier_timeline_null_dates_sorted_last():
    """Events with null occurred_at are sorted last."""
    case_id = uuid.uuid4()
    signal_id = uuid.uuid4()
    event_id_dated = uuid.uuid4()
    event_id_null = uuid.uuid4()

    case = _make_case(case_id)

    signal_row = _make_signal_row(
        signal_id,
        event_ids=[str(event_id_dated), str(event_id_null)],
        entity_ids=[],
    )

    event_dated = _make_event(event_id_dated, occurred_at=datetime(2025, 3, 1, tzinfo=timezone.utc))
    event_null = SimpleNamespace(
        id=event_id_null,
        type="contrato",
        description=None,
        occurred_at=None,
        source_connector="pncp",
        value_brl=None,
        attrs={},
    )

    call_count = 0

    class _FakeSession:
        async def execute(self, stmt, params=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _ExecResult(scalar=case)
            if call_count == 2:
                return _ExecResult(rows=[signal_row])
            if call_count == 3:
                return _ExecResult(scalar_values=[])
            if call_count == 4:
                return _ExecResult(rows=[])
            raise AssertionError(f"Unexpected call {call_count}")

    chunked_calls = []

    async def _ordered_chunked_in(_session, stmt_factory, ids, **kwargs):
        chunked_calls.append(list(ids))
        call_idx = len(chunked_calls)
        if call_idx == 1:
            return [event_null, event_dated]
        if call_idx == 2:
            return []
        if call_idx == 3:
            return []
        return []

    with patch("shared.utils.query.execute_chunked_in", side_effect=_ordered_chunked_in):
        result = await queries.get_dossier_timeline(_FakeSession(), case_id)

    assert len(result["events"]) == 2
    assert result["events"][0]["id"] == str(event_id_dated)  # dated first
    assert result["events"][1]["id"] == str(event_id_null)  # null last
