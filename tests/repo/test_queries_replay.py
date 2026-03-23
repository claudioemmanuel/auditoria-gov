from datetime import datetime, timezone
from types import SimpleNamespace
import uuid

from shared.repo.queries import build_signal_replay_hash


def test_build_signal_replay_hash_is_deterministic():
    signal = SimpleNamespace(
        id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        typology_id=uuid.UUID("00000000-0000-0000-0000-000000000010"),
        severity="high",
        data_completeness=0.91,
        title="Teste",
        summary="Resumo",
        completeness_score=0.8,
        completeness_status="sufficient",
        factors={"k": "v"},
        evidence_refs=[{"ref_type": "event", "ref_id": "x", "description": "desc"}],
        entity_ids=["a"],
        event_ids=["b"],
        period_start=datetime(2025, 1, 1, tzinfo=timezone.utc),
        period_end=datetime(2025, 1, 31, tzinfo=timezone.utc),
    )
    package = SimpleNamespace(
        id=uuid.UUID("00000000-0000-0000-0000-000000000100"),
        source_url="https://example.com",
        source_hash="abc",
        captured_at=datetime(2025, 2, 1, tzinfo=timezone.utc),
        parser_version="typology:T01",
        model_version="gpt-4o-mini",
        raw_snapshot_uri="raw://x",
        normalized_snapshot_uri="signal://x",
    )

    first = build_signal_replay_hash(signal, package)
    second = build_signal_replay_hash(signal, package)

    assert first == second
    assert len(first) == 64
