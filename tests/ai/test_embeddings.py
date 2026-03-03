from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shared.ai.embeddings import embed_texts


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
