"""Tests for the semantic ER matching pass (_build_semantic_matches).

Covers:
- Edge cases: all matched, no embeddings, large datasets
- Same-type filtering, deduplication of pairs, match result fields
- Integration-style: semantic_matches count in run_entity_resolution result
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest

from worker.tasks.er_tasks import _build_semantic_matches


def _entity(
    name: str,
    entity_type: str = "company",
    entity_id: uuid.UUID | None = None,
):
    return {
        "id": entity_id or uuid.uuid4(),
        "name": name,
        "type": entity_type,
        "identifiers": {},
        "attrs": {},
    }


class TestBuildSemanticMatches:
    def test_returns_empty_when_all_matched(self):
        """All entities already in matched_ids: returns empty list."""
        e1 = _entity("Empresa A")
        e2 = _entity("Empresa B")
        matched_ids = {e1["id"], e2["id"]}
        session = MagicMock()

        result = _build_semantic_matches(session, [e1, e2], matched_ids)

        assert result == []
        session.execute.assert_not_called()

    def test_returns_empty_when_no_embeddings(self):
        """get_entity_embeddings_for_er returns empty dict: returns empty list."""
        e1 = _entity("Empresa A")
        session = MagicMock()

        # Patch at source module because _build_semantic_matches does:
        #   from shared.repo.queries import get_entity_embeddings_for_er
        with patch(
            "shared.repo.queries.get_entity_embeddings_for_er",
            return_value={},
        ):
            result = _build_semantic_matches(session, [e1], set())

        assert result == []

    def test_skips_large_datasets(self):
        """len(unmatched) > 10_000: returns empty list and logs warning."""
        entities = [_entity(f"Entity {i}") for i in range(10_001)]
        session = MagicMock()

        with patch("worker.tasks.er_tasks.log") as mock_log:
            result = _build_semantic_matches(session, entities, set())

        assert result == []
        mock_log.warning.assert_called_once()
        assert "semantic_skipped_large_dataset" in mock_log.warning.call_args[0][0]

    def test_matches_same_type_only(self):
        """Two entities with similar embeddings but different types: no match."""
        e1_id = uuid.uuid4()
        e2_id = uuid.uuid4()
        e1 = _entity("Empresa Alfa", entity_type="company", entity_id=e1_id)
        e2 = _entity("Empresa Alfa", entity_type="person", entity_id=e2_id)

        embeddings_map = {
            str(e1_id): [0.1] * 1536,
            str(e2_id): [0.1] * 1536,
        }

        session = MagicMock()
        call_count = {"n": 0}
        def _fake_execute(sql, params=None):
            call_count["n"] += 1
            result = MagicMock()
            if call_count["n"] == 1:
                return result  # SET LOCAL
            elif call_count["n"] == 2:
                # Query for e1 -> returns e2 as neighbor (different type)
                row = MagicMock()
                row.source_id = str(e2_id)
                row.distance = 0.05
                result.fetchall.return_value = [row]
            elif call_count["n"] == 3:
                # Query for e2 -> returns e1 as neighbor (different type)
                row = MagicMock()
                row.source_id = str(e1_id)
                row.distance = 0.05
                result.fetchall.return_value = [row]
            return result

        session.execute = _fake_execute

        with patch(
            "shared.repo.queries.get_entity_embeddings_for_er",
            return_value=embeddings_map,
        ):
            result = _build_semantic_matches(session, [e1, e2], set())

        # Different types: should not match
        assert result == []

    def test_matches_same_type_similar(self):
        """Two entities with similar embeddings and same type: returns MatchResult."""
        e1_id = uuid.uuid4()
        e2_id = uuid.uuid4()
        e1 = _entity("Empresa Alfa LTDA", entity_type="company", entity_id=e1_id)
        e2 = _entity("Empresa Alpha LTDA", entity_type="company", entity_id=e2_id)

        embeddings_map = {
            str(e1_id): [0.1] * 1536,
            str(e2_id): [0.1] * 1536,
        }

        mock_row = MagicMock()
        mock_row.source_id = str(e2_id)
        mock_row.distance = 0.08  # distance <= 0.12 threshold

        session = MagicMock()
        call_count = {"n": 0}
        def _fake_execute(sql, params=None):
            call_count["n"] += 1
            result = MagicMock()
            if call_count["n"] == 1:
                return result  # SET LOCAL
            elif call_count["n"] == 2:
                # query for e1 -> returns e2 as neighbor
                result.fetchall.return_value = [mock_row]
            else:
                # query for e2 -> returns e1 but pair already checked
                mock_row2 = MagicMock()
                mock_row2.source_id = str(e1_id)
                mock_row2.distance = 0.08
                result.fetchall.return_value = [mock_row2]
            return result

        session.execute = _fake_execute

        with patch(
            "shared.repo.queries.get_entity_embeddings_for_er",
            return_value=embeddings_map,
        ):
            result = _build_semantic_matches(session, [e1, e2], set())

        assert len(result) == 1
        match = result[0]
        assert match.match_type == "semantic"
        assert match.score == pytest.approx(1.0 - 0.08, abs=0.001)

    def test_deduplicates_pairs(self):
        """A->B and B->A discovered: only one MatchResult emitted."""
        e1_id = uuid.uuid4()
        e2_id = uuid.uuid4()
        e1 = _entity("Empresa X", entity_type="company", entity_id=e1_id)
        e2 = _entity("Empresa Y", entity_type="company", entity_id=e2_id)

        embeddings_map = {
            str(e1_id): [0.1] * 1536,
            str(e2_id): [0.1] * 1536,
        }

        session = MagicMock()
        call_count = {"n": 0}
        def _fake_execute(sql, params=None):
            call_count["n"] += 1
            result = MagicMock()
            if call_count["n"] == 1:
                return result  # SET LOCAL
            elif call_count["n"] == 2:
                # e1 query -> e2 found
                row = MagicMock()
                row.source_id = str(e2_id)
                row.distance = 0.05
                result.fetchall.return_value = [row]
            elif call_count["n"] == 3:
                # e2 query -> e1 found (duplicate pair)
                row = MagicMock()
                row.source_id = str(e1_id)
                row.distance = 0.05
                result.fetchall.return_value = [row]
            return result

        session.execute = _fake_execute

        with patch(
            "shared.repo.queries.get_entity_embeddings_for_er",
            return_value=embeddings_map,
        ):
            result = _build_semantic_matches(session, [e1, e2], set())

        # Only one match despite both directions being discovered
        assert len(result) == 1

    def test_match_result_fields(self):
        """MatchResult has correct score (1.0 - distance) and reason with cosine similarity."""
        e1_id = uuid.uuid4()
        e2_id = uuid.uuid4()
        e1 = _entity("Construtora ABC", entity_type="company", entity_id=e1_id)
        e2 = _entity("Construtora ABD", entity_type="company", entity_id=e2_id)

        embeddings_map = {
            str(e1_id): [0.2] * 1536,
        }

        mock_row = MagicMock()
        mock_row.source_id = str(e2_id)
        mock_row.distance = 0.10

        session = MagicMock()
        call_count = {"n": 0}
        def _fake_execute(sql, params=None):
            call_count["n"] += 1
            result = MagicMock()
            if call_count["n"] == 1:
                return result  # SET LOCAL
            result.fetchall.return_value = [mock_row]
            return result

        session.execute = _fake_execute

        with patch(
            "shared.repo.queries.get_entity_embeddings_for_er",
            return_value=embeddings_map,
        ):
            result = _build_semantic_matches(session, [e1, e2], set())

        assert len(result) == 1
        match = result[0]
        assert match.score == pytest.approx(0.90, abs=0.001)
        assert "cosine similarity" in match.reason
        assert match.entity_a_id == e1_id
        assert match.entity_b_id == e2_id


class TestRunEntityResolutionSemanticPass:
    def test_sem_count_in_result_when_provider_none(self):
        """LLM_PROVIDER=none: semantic_matches=0 in result dict."""
        from worker.tasks import er_tasks

        fake_entity_a = MagicMock()
        fake_entity_a.id = uuid.uuid4()
        fake_entity_a.name = "Entity A"
        fake_entity_a.type = "company"
        fake_entity_a.identifiers = {}
        fake_entity_a.attrs = {}
        fake_entity_a.cluster_id = None

        fake_entity_b = MagicMock()
        fake_entity_b.id = uuid.uuid4()
        fake_entity_b.name = "Entity B"
        fake_entity_b.type = "company"
        fake_entity_b.identifiers = {}
        fake_entity_b.attrs = {}
        fake_entity_b.cluster_id = None

        mock_session = MagicMock()

        exec_results = iter([
            # watermark query -> None
            MagicMock(scalar_one_or_none=MagicMock(return_value=None)),
            # entities query -> 2 entities
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[fake_entity_a, fake_entity_b])))),
            # participants query -> empty
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))),
        ])

        def _fake_execute(stmt, *a, **kw):
            try:
                return next(exec_results)
            except StopIteration:
                return MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[]))))

        mock_session.execute = _fake_execute
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)

        with patch("shared.db_sync.SyncSession", return_value=mock_session), \
             patch("shared.config.settings") as mock_settings, \
             patch.object(er_tasks, "_build_deterministic_matches", return_value=[]), \
             patch.object(er_tasks, "_build_probabilistic_matches", return_value=[]), \
             patch("shared.er.clustering.cluster_entities", return_value=[]), \
             patch("shared.er.edges.build_structural_edges", return_value=[]):
            mock_settings.LLM_PROVIDER = "none"
            result = er_tasks.run_entity_resolution()

        assert result["semantic_matches"] == 0

    def test_sem_count_in_result_when_provider_active(self):
        """LLM_PROVIDER=openai: semantic_matches key present in result dict."""
        from shared.er.matching import MatchResult
        from worker.tasks import er_tasks

        fake_entity_a = MagicMock()
        fake_entity_a.id = uuid.uuid4()
        fake_entity_a.name = "Entity A"
        fake_entity_a.type = "company"
        fake_entity_a.identifiers = {}
        fake_entity_a.attrs = {}

        fake_entity_b = MagicMock()
        fake_entity_b.id = uuid.uuid4()
        fake_entity_b.name = "Entity B"
        fake_entity_b.type = "company"
        fake_entity_b.identifiers = {}
        fake_entity_b.attrs = {}

        sem_match = MatchResult(
            entity_a_id=fake_entity_a.id,
            entity_b_id=fake_entity_b.id,
            match_type="semantic",
            score=0.92,
            reason="Embedding cosine similarity: 0.920",
        )

        mock_session = MagicMock()

        exec_results = iter([
            MagicMock(scalar_one_or_none=MagicMock(return_value=None)),
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[fake_entity_a, fake_entity_b])))),
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))),
        ])

        def _fake_execute(stmt, *a, **kw):
            try:
                return next(exec_results)
            except StopIteration:
                return MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[]))))

        mock_session.execute = _fake_execute
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)

        with patch("shared.db_sync.SyncSession", return_value=mock_session), \
             patch("shared.config.settings") as mock_settings, \
             patch.object(er_tasks, "_build_deterministic_matches", return_value=[]), \
             patch.object(er_tasks, "_build_probabilistic_matches", return_value=[]), \
             patch.object(er_tasks, "_build_semantic_matches", return_value=[sem_match]), \
             patch("shared.er.clustering.cluster_entities", return_value=[]), \
             patch("shared.er.edges.build_structural_edges", return_value=[]):
            mock_settings.LLM_PROVIDER = "openai"
            result = er_tasks.run_entity_resolution()

        assert result["semantic_matches"] == 1
