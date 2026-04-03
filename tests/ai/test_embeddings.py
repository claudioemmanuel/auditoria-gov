import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shared.ai.embeddings import embed_entity, embed_signal_summary, embed_texts


class TestEmbedTexts:
    @pytest.mark.asyncio
    async def test_empty_texts_returns_immediately(self):
        session = AsyncMock()
        await embed_texts([], "test", [], session)
        session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_stores_corpus_and_embeddings(self):
        mock_provider = AsyncMock()
        mock_provider.embed.return_value = [[0.1, 0.2], [0.3, 0.4]]

        session = AsyncMock()

        corpus1 = MagicMock()
        corpus1.id = "corpus-1"
        corpus2 = MagicMock()
        corpus2.id = "corpus-2"

        with patch("shared.ai.embeddings.get_llm_provider", return_value=mock_provider), \
             patch.dict("sys.modules", {}), \
             patch("shared.models.orm.TextCorpus", side_effect=[corpus1, corpus2]) as MockCorpus, \
             patch("shared.models.orm.TextEmbedding") as MockEmb, \
             patch("shared.config.settings") as mock_settings:
            mock_settings.EMBEDDING_MODEL = "test-model"

            await embed_texts(
                ["text1", "text2"], "licitacao", ["src-1", "src-2"], session
            )

            assert session.add.call_count == 4  # 2 corpus + 2 embeddings
            session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_single_text(self):
        mock_provider = AsyncMock()
        mock_provider.embed.return_value = [[0.5, 0.6]]

        session = AsyncMock()

        with patch("shared.ai.embeddings.get_llm_provider", return_value=mock_provider):
            await embed_texts(["hello"], "doc", ["s1"], session)

            mock_provider.embed.assert_awaited_once_with(["hello"])
            assert session.add.call_count == 2
            session.commit.assert_awaited_once()


def _mock_execute_returning(value):
    """Helper: build an AsyncMock session.execute that returns scalar_one_or_none = value."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = value
    execute = AsyncMock(return_value=mock_result)
    return execute


class TestEmbedEntity:
    @pytest.mark.asyncio
    async def test_creates_corpus_and_embedding(self):
        """New entity name creates TextCorpus + TextEmbedding and flushes."""
        entity_id = uuid.uuid4()
        session = AsyncMock()

        # First execute: corpus lookup -> None (not found)
        # Second execute: embedding lookup -> None (not found)
        corpus_mock = MagicMock()
        corpus_mock.id = uuid.uuid4()

        call_count = {"n": 0}
        async def _fake_execute(stmt, *a, **kw):
            call_count["n"] += 1
            result = MagicMock()
            result.scalar_one_or_none.return_value = None
            return result

        session.execute = _fake_execute

        mock_provider = AsyncMock()
        mock_provider.embed.return_value = [[0.1] * 1536]

        with patch("shared.ai.embeddings.get_llm_provider", return_value=mock_provider), \
             patch("shared.config.settings") as mock_settings:
            mock_settings.EMBEDDING_MODEL = "test-model"
            await embed_entity(session, entity_id, "empresa alfa ltda")

        # Should have called session.add at least twice (corpus + embedding)
        assert session.add.call_count >= 2
        # Should have flushed at least twice (after corpus, after embedding)
        assert session.flush.await_count >= 2

    @pytest.mark.asyncio
    async def test_skips_empty_name(self):
        """Empty name_normalized causes early return with no DB operations."""
        session = AsyncMock()
        await embed_entity(session, uuid.uuid4(), "")
        session.add.assert_not_called()
        session.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_upsert_existing_same_name(self):
        """Corpus exists with same content: skips re-embedding when embedding exists."""
        entity_id = uuid.uuid4()
        session = AsyncMock()

        existing_corpus = MagicMock()
        existing_corpus.id = uuid.uuid4()
        existing_corpus.content = "empresa alfa"

        existing_embedding = MagicMock()

        calls = {"n": 0}
        async def _fake_execute(stmt, *a, **kw):
            calls["n"] += 1
            result = MagicMock()
            if calls["n"] == 1:
                # corpus lookup -> found
                result.scalar_one_or_none.return_value = existing_corpus
            else:
                # embedding lookup -> found
                result.scalar_one_or_none.return_value = existing_embedding
            return result

        session.execute = _fake_execute

        await embed_entity(session, entity_id, "empresa alfa")

        # No new corpus or embedding added; early return
        session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_upsert_changed_name(self):
        """Corpus exists with different content: deletes old embedding, creates new."""
        entity_id = uuid.uuid4()
        session = AsyncMock()

        existing_corpus = MagicMock()
        existing_corpus.id = uuid.uuid4()
        existing_corpus.content = "old name"

        old_embedding = MagicMock()

        calls = {"n": 0}
        async def _fake_execute(stmt, *a, **kw):
            calls["n"] += 1
            result = MagicMock()
            if calls["n"] == 1:
                # corpus lookup -> found with different content
                result.scalar_one_or_none.return_value = existing_corpus
            elif calls["n"] == 2:
                # old embedding lookup (for deletion)
                result.scalar_one_or_none.return_value = old_embedding
            else:
                # embedding exists check after deletion -> None
                result.scalar_one_or_none.return_value = None
            return result

        session.execute = _fake_execute

        mock_provider = AsyncMock()
        mock_provider.embed.return_value = [[0.5] * 1536]

        with patch("shared.ai.embeddings.get_llm_provider", return_value=mock_provider), \
             patch("shared.config.settings") as mock_settings:
            mock_settings.EMBEDDING_MODEL = "test-model"
            await embed_entity(session, entity_id, "new name")

        # Old embedding deleted
        session.delete.assert_awaited_once_with(old_embedding)
        # Corpus content updated
        assert existing_corpus.content == "new name"
        # New embedding added
        assert session.add.call_count >= 1
        mock_provider.embed.assert_awaited_once_with(["new name"])

    @pytest.mark.asyncio
    async def test_already_embedded(self):
        """Corpus + embedding exist with same name: returns early, no new embedding."""
        entity_id = uuid.uuid4()
        session = AsyncMock()

        existing_corpus = MagicMock()
        existing_corpus.id = uuid.uuid4()
        existing_corpus.content = "empresa alfa"

        existing_embedding = MagicMock()

        calls = {"n": 0}
        async def _fake_execute(stmt, *a, **kw):
            calls["n"] += 1
            result = MagicMock()
            if calls["n"] == 1:
                result.scalar_one_or_none.return_value = existing_corpus
            else:
                result.scalar_one_or_none.return_value = existing_embedding
            return result

        session.execute = _fake_execute

        mock_provider = AsyncMock()

        with patch("shared.ai.embeddings.get_llm_provider", return_value=mock_provider):
            await embed_entity(session, entity_id, "empresa alfa")

        # Provider never called because embedding already exists
        mock_provider.embed.assert_not_awaited()
        session.add.assert_not_called()


class TestEmbedSignalSummary:
    @pytest.mark.asyncio
    async def test_creates_corpus_and_embedding(self):
        """New signal summary creates TextCorpus + TextEmbedding."""
        signal_id = uuid.uuid4()
        session = AsyncMock()

        calls = {"n": 0}
        async def _fake_execute(stmt, *a, **kw):
            calls["n"] += 1
            result = MagicMock()
            result.scalar_one_or_none.return_value = None
            return result

        session.execute = _fake_execute

        mock_provider = AsyncMock()
        mock_provider.embed.return_value = [[0.2] * 1536]

        with patch("shared.ai.embeddings.get_llm_provider", return_value=mock_provider), \
             patch("shared.config.settings") as mock_settings:
            mock_settings.EMBEDDING_MODEL = "test-model"
            await embed_signal_summary(session, signal_id, "Risk of vendor concentration")

        assert session.add.call_count >= 2
        assert session.flush.await_count >= 2
        mock_provider.embed.assert_awaited_once_with(["Risk of vendor concentration"])

    @pytest.mark.asyncio
    async def test_skips_empty_summary(self):
        """Empty summary causes early return with no DB operations."""
        session = AsyncMock()
        await embed_signal_summary(session, uuid.uuid4(), "")
        session.add.assert_not_called()
        session.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_already_embedded(self):
        """Existing corpus + embedding: returns early, no new embedding."""
        signal_id = uuid.uuid4()
        session = AsyncMock()

        existing_corpus = MagicMock()
        existing_corpus.id = uuid.uuid4()
        existing_embedding = MagicMock()

        calls = {"n": 0}
        async def _fake_execute(stmt, *a, **kw):
            calls["n"] += 1
            result = MagicMock()
            if calls["n"] == 1:
                result.scalar_one_or_none.return_value = existing_corpus
            else:
                result.scalar_one_or_none.return_value = existing_embedding
            return result

        session.execute = _fake_execute

        mock_provider = AsyncMock()
        with patch("shared.ai.embeddings.get_llm_provider", return_value=mock_provider):
            await embed_signal_summary(session, signal_id, "some summary")

        mock_provider.embed.assert_not_awaited()
        session.add.assert_not_called()
