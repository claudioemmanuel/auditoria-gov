import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, call

from openwatch_models.canonical import CanonicalEntity, CanonicalEvent
from openwatch_db.upsert_sync import (
    _normalize_identifiers,
    batch_prefetch_entities,
    batch_upsert_events,
    batch_upsert_participants,
    upsert_entity_sync,
    upsert_entity_with_lookup,
    upsert_event_sync,
)


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


# ── batch_prefetch_entities ──────────────────────────────────────────────────

def _scalars_all_result(values):
    """Mock for select().scalars().all() pattern."""
    r = MagicMock()
    r.scalars.return_value.all.return_value = values
    return r


def test_batch_prefetch_entities_issues_two_in_queries():
    """batch_prefetch_entities must issue at most 2 IN queries (CNPJ + cpf_hash)
    for a mixed batch of canonicals, not one query per entity."""
    cnpj_entity = MagicMock()
    cnpj_entity.identifiers = {"cnpj": "12345678000195"}

    cpf_entity = MagicMock()
    cpf_entity.identifiers = {"cpf_hash": "abc123hash", "cpf": "21576805867"}

    session = MagicMock()
    session.execute.side_effect = [
        _scalars_all_result([cnpj_entity]),   # CNPJ IN query
        _scalars_all_result([cpf_entity]),     # cpf_hash IN query
    ]

    canonicals = [
        CanonicalEntity(
            source_connector="c", source_id="1", type="company",
            name="Empresa X", identifiers={"cnpj": "12.345.678/0001-95"}, attrs={},
        ),
        CanonicalEntity(
            source_connector="c", source_id="2", type="person",
            name="Joao", identifiers={"cpf": "215.768.058-67"}, attrs={},
        ),
    ]

    result = batch_prefetch_entities(session, canonicals)

    assert session.execute.call_count == 2
    assert "cnpj:12345678000195" in result
    assert result["cnpj:12345678000195"] is cnpj_entity
    assert "cpf_hash:abc123hash" in result
    assert result["cpf_hash:abc123hash"] is cpf_entity


def test_batch_prefetch_entities_empty_list():
    """batch_prefetch_entities with no canonicals makes no DB calls."""
    session = MagicMock()
    result = batch_prefetch_entities(session, [])
    session.execute.assert_not_called()
    assert result == {}


def test_batch_prefetch_entities_no_identifiers():
    """Canonicals with neither CNPJ nor CPF produce no IN queries."""
    session = MagicMock()
    canonicals = [
        CanonicalEntity(
            source_connector="c", source_id="1", type="org",
            name="Secretaria X", identifiers={}, attrs={},
        ),
    ]
    result = batch_prefetch_entities(session, canonicals)
    session.execute.assert_not_called()
    assert result == {}


# ── upsert_entity_with_lookup ────────────────────────────────────────────────

def test_upsert_entity_with_lookup_hits_cache_no_db():
    """When entity is pre-fetched in the lookup dict, no DB query is issued."""
    existing = MagicMock()
    existing.attrs = {"a": 1}
    existing.name = "Empresa"
    existing.identifiers = {"cnpj": "12345678000195"}

    lookup = {"cnpj:12345678000195": existing}
    session = MagicMock()

    canonical = CanonicalEntity(
        source_connector="c", source_id="1", type="company",
        name="Empresa Atualizada", identifiers={"cnpj": "12.345.678/0001-95"},
        attrs={"b": 2},
    )

    result = upsert_entity_with_lookup(session, canonical, lookup)

    session.execute.assert_not_called()
    assert result is existing
    assert existing.attrs == {"a": 1, "b": 2}


def test_upsert_entity_with_lookup_creates_and_updates_lookup():
    """When entity is not in lookup, a new Entity is created and the lookup updated."""
    session = MagicMock()
    # No existing entity — execute returns empty for org name fallback
    r = MagicMock()
    r.scalars.return_value.first.return_value = None
    session.execute.return_value = r

    lookup: dict = {}

    canonical = CanonicalEntity(
        source_connector="c", source_id="1", type="person",
        name="Maria Silva", identifiers={"cpf": "215.768.058-67"}, attrs={},
    )

    result = upsert_entity_with_lookup(session, canonical, lookup)

    session.add.assert_called_once_with(result)
    cpf_hash = _normalize_identifiers({"cpf": "21576805867"})["cpf_hash"]
    assert f"cpf_hash:{cpf_hash}" in lookup
    assert lookup[f"cpf_hash:{cpf_hash}"] is result


def test_upsert_entity_with_lookup_second_entity_same_cpf_uses_cache():
    """Second canonical with the same CPF finds the first entity via the updated lookup."""
    session = MagicMock()
    lookup: dict = {}

    canonical1 = CanonicalEntity(
        source_connector="c", source_id="1", type="person",
        name="Maria Silva", identifiers={"cpf": "21576805867"}, attrs={"a": 1},
    )
    canonical2 = CanonicalEntity(
        source_connector="c", source_id="2", type="person",
        name="Maria S.", identifiers={"cpf": "21576805867"}, attrs={"b": 2},
    )

    # No existing entities in DB
    r = MagicMock()
    r.scalars.return_value.first.return_value = None
    session.execute.return_value = r

    entity1 = upsert_entity_with_lookup(session, canonical1, lookup)
    entity2 = upsert_entity_with_lookup(session, canonical2, lookup)

    # Both should resolve to the same object.
    # Person entities have no name-based fallback, so no DB queries are issued.
    assert entity1 is entity2
    session.execute.assert_not_called()
    # First entity is created (add called once), second is a cache hit (no add).
    session.add.assert_called_once()


# ── batch_upsert_events ──────────────────────────────────────────────────────

def test_batch_upsert_events_returns_dict_keyed_by_source():
    """batch_upsert_events returns a dict keyed by (source_connector, source_id)."""
    ev1 = MagicMock()
    ev1.source_connector = "senado"
    ev1.source_id = "ceaps:1"

    ev2 = MagicMock()
    ev2.source_connector = "senado"
    ev2.source_id = "ceaps:2"

    session = MagicMock()
    # First execute is PNCP enrichment lookup (returns nothing), second is batch INSERT
    pncp_result = MagicMock()
    pncp_result.scalars.return_value.all.return_value = []

    insert_result = MagicMock()
    insert_result.scalars.return_value = iter([ev1, ev2])

    session.execute.side_effect = [insert_result]

    now = datetime(2025, 1, 1, tzinfo=timezone.utc)
    canonicals = [
        CanonicalEvent(
            source_connector="senado", source_id="ceaps:1",
            type="despesa", subtype=None, description="D1",
            occurred_at=now, value_brl=100.0, attrs={},
        ),
        CanonicalEvent(
            source_connector="senado", source_id="ceaps:2",
            type="despesa", subtype=None, description="D2",
            occurred_at=now, value_brl=200.0, attrs={},
        ),
    ]

    result = batch_upsert_events(session, canonicals)

    assert ("senado", "ceaps:1") in result
    assert ("senado", "ceaps:2") in result
    assert result[("senado", "ceaps:1")] is ev1
    assert result[("senado", "ceaps:2")] is ev2


def test_batch_upsert_events_empty_returns_empty_dict():
    session = MagicMock()
    assert batch_upsert_events(session, []) == {}
    session.execute.assert_not_called()


# ── batch_upsert_participants ────────────────────────────────────────────────

def test_batch_upsert_participants_empty_is_noop():
    session = MagicMock()
    batch_upsert_participants(session, [])
    session.execute.assert_not_called()


def test_batch_upsert_participants_single_batch():
    """A list under the batch limit produces exactly one execute call."""
    session = MagicMock()
    rows = [
        (uuid.uuid4(), uuid.uuid4(), "buyer", {"x": 1}),
        (uuid.uuid4(), uuid.uuid4(), "supplier", None),
    ]
    batch_upsert_participants(session, rows)
    session.execute.assert_called_once()
