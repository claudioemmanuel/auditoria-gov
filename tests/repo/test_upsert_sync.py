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


def test_upsert_entity_sync_handles_duplicate_org_names():
    """Name-based fallback for org/company must not raise MultipleResultsFound.

    Regression: scalar_one_or_none() raised MultipleResultsFound when two
    entities with the same (type, name_normalized) existed in the DB.
    Fix: use .limit(1).scalars().first() instead.
    """
    existing_a = MagicMock()
    existing_a.attrs = {"src": "a"}
    existing_a.name = "Ministério da Educação"

    existing_b = MagicMock()
    existing_b.attrs = {"src": "b"}
    existing_b.name = "Ministério da Educação"

    def _name_result(value):
        r = MagicMock()
        r.scalars.return_value.first.return_value = value
        r.scalar_one_or_none.side_effect = Exception("must not call scalar_one_or_none")
        return r

    # canonical has identifiers={} → _find_existing_entity_by_strong_identifier
    # makes zero session.execute calls (no CNPJ, no CPF hash).
    # Only the name-based org fallback fires → single execute call.
    session = MagicMock()
    session.execute.side_effect = [
        _name_result(existing_a),  # name lookup — returns first match, no error
    ]

    canonical = CanonicalEntity(
        source_connector="compras_gov",
        source_id="org:1",
        type="org",
        name="Ministério da Educação",
        identifiers={},
        attrs={"new": "z"},
    )

    returned = upsert_entity_sync(session, canonical)

    assert returned is existing_a
    session.add.assert_not_called()


def test_normalize_identifiers_preserves_cpf_and_adds_hash():
    normalized = _normalize_identifiers({"cpf": "215.768.058-67"})
    assert normalized["cpf"] == "21576805867"
    assert normalized["cpf_hash"]
    assert "cpf_masked" not in normalized
