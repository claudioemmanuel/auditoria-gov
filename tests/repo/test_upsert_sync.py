from datetime import datetime, timezone
from unittest.mock import MagicMock

from shared.models.canonical import CanonicalEntity, CanonicalEvent
from shared.repo.upsert_sync import _normalize_identifiers, upsert_entity_sync, upsert_event_sync


def _scalar_result(value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _scalar_one_result(value):
    """Mock for INSERT...RETURNING which uses scalar_one() (not _or_none)."""
    result = MagicMock()
    result.scalar_one.return_value = value
    return result


def test_upsert_entity_sync_deduplicates_by_cpf():
    existing = MagicMock()
    existing.attrs = {"existing": "x"}

    session = MagicMock()
    session.execute.return_value = _scalar_result(existing)

    canonical = CanonicalEntity(
        source_connector="portal_transparencia",
        source_id="person:1",
        type="person",
        name="Joao da Silva",
        identifiers={"cpf": "21576805867"},
        attrs={"new": "y"},
    )

    returned = upsert_entity_sync(session, canonical)

    assert returned is existing
    assert existing.attrs == {"existing": "x", "new": "y"}
    session.add.assert_not_called()


def test_upsert_event_sync_returns_event_via_on_conflict():
    """upsert_event_sync now uses INSERT...ON CONFLICT DO UPDATE...RETURNING."""
    returned_event = MagicMock()
    returned_event.type = "despesa"
    returned_event.subtype = "ceaps"
    returned_event.occurred_at = datetime(2025, 2, 7, tzinfo=timezone.utc)
    returned_event.value_brl = 1000.0

    session = MagicMock()
    session.execute.return_value = _scalar_one_result(returned_event)

    canonical = CanonicalEvent(
        source_connector="senado",
        source_id="ceaps:2025:1:0",
        type="despesa",
        subtype="ceaps",
        description="Despesa de cota parlamentar",
        occurred_at=datetime(2025, 2, 7, tzinfo=timezone.utc),
        value_brl=1000.0,
        attrs={"modality": "dispensa"},
    )

    result = upsert_event_sync(session, canonical)

    assert result is returned_event
    session.execute.assert_called_once()


def test_normalize_identifiers_hashes_cpf_and_removes_raw_value():
    normalized = _normalize_identifiers({"cpf": "215.768.058-67"})
    assert "cpf" not in normalized
    assert normalized["cpf_hash"]
    assert normalized["cpf_masked"] == "***.***058-67"
