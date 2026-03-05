import uuid

from worker.tasks import er_tasks


def _entity(
    name: str,
    entity_type: str = "company",
    identifiers: dict | None = None,
    attrs: dict | None = None,
):
    return {
        "id": uuid.uuid4(),
        "name": name,
        "type": entity_type,
        "identifiers": identifiers or {},
        "attrs": attrs or {},
    }


def test_build_deterministic_matches_groups_by_identifier():
    same_cnpj = "11.222.333/0001-81"
    entities = [
        _entity("Empresa A", identifiers={"cnpj": same_cnpj}),
        _entity("Empresa B", identifiers={"cnpj": same_cnpj}),
        _entity("Empresa C", identifiers={"cnpj": "99.888.777/0001-66"}),
    ]

    matches = er_tasks._build_deterministic_matches(entities)

    assert len(matches) == 1
    assert matches[0].match_type == "deterministic"
    assert "CNPJ match" in matches[0].reason


def test_build_probabilistic_matches_uses_blocking():
    entities = [
        _entity("EMPRESA ALFA LOGISTICA LTDA"),
        _entity("EMPRESA ALFA LOGISTICA"),
        _entity("ASSOCIACAO CULTURAL BETA"),
    ]

    matches = er_tasks._build_probabilistic_matches(entities, matched_ids=set())

    assert matches
    assert any(m.match_type == "probabilistic" for m in matches)


def test_should_run_probabilistic_respects_entity_volume_limit():
    assert er_tasks._should_run_probabilistic(1000) is True
    assert er_tasks._should_run_probabilistic(6000) is False


# ── Regression: IN clause parameter overflow ─────────────────────────────────
# Bug: _flush_edges built IN clauses with all entity IDs at once. When the number
# of IDs exceeded ~21845 (3 params per row × 21845 = 65535), psycopg raised:
#   OperationalError: number of parameters must be between 0 and 65535
# Fix: _IN_CHUNK = 5_000 — all IN queries are chunked to stay well below the limit.

def test_in_chunk_constant_prevents_parameter_overflow():
    """_IN_CHUNK must be ≤ 5000 so that 3 IN-clause queries × _IN_CHUNK stay below 65535."""
    assert hasattr(er_tasks, "_IN_CHUNK"), "_IN_CHUNK constant missing from er_tasks"
    assert er_tasks._IN_CHUNK <= 5_000, (
        f"_IN_CHUNK={er_tasks._IN_CHUNK} is too large — risks psycopg 65535 parameter limit"
    )
    # Three IN clauses per chunk (GraphNode, Entity, GraphEdge). Must stay safe.
    assert er_tasks._IN_CHUNK * 3 < 65_535


# ── Regression: Advisory lock prevents concurrent ER deadlocks ───────────────
# Bug: worker-cpu ran with concurrency=2, causing two ER tasks to run in parallel.
# Both would UPDATE entity SET er_processed_at=... simultaneously → DeadlockDetected.
# Fix: pg_try_advisory_lock(7349812) at task start — second worker returns "skipped".

def test_run_entity_resolution_skips_when_advisory_lock_not_acquired():
    """When pg_try_advisory_lock returns False, task must return skipped immediately."""
    from unittest.mock import MagicMock, patch

    mock_session = MagicMock()
    mock_session.__enter__ = MagicMock(return_value=mock_session)
    mock_session.__exit__ = MagicMock(return_value=False)
    # Simulate lock already held by another worker
    mock_session.execute.return_value.scalar.return_value = False

    with patch("shared.db_sync.SyncSession", return_value=mock_session):
        result = er_tasks.run_entity_resolution()

    assert result["status"] == "skipped"
    assert result["reason"] == "concurrent run in progress"
    # Must stop immediately — only one execute call (the lock check)
    assert mock_session.execute.call_count == 1
