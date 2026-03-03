from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from shared.ai.rag import retrieve_context


class TestRetrieveContext:
    @pytest.mark.asyncio
    async def test_returns_results(self):
        mock_provider = AsyncMock()
        mock_provider.embed.return_value = [[0.1, 0.2, 0.3]]

        row1 = MagicMock()
        row1.id = uuid4()
        row1.source_type = "licitacao"
        row1.source_id = "src-1"
        row1.content = "Texto de exemplo"
        row1.similarity = 0.95

        row2 = MagicMock()
        row2.id = uuid4()
        row2.source_type = "contrato"
        row2.source_id = "src-2"
        row2.content = "Outro texto"
        row2.similarity = 0.80

        mock_result = MagicMock()
        mock_result.fetchall.return_value = [row1, row2]

        session = AsyncMock()
        session.execute.return_value = mock_result

        with patch("shared.ai.rag.get_llm_provider", return_value=mock_provider):
            results = await retrieve_context("busca", session, limit=5)

            assert len(results) == 2
            assert results[0]["source_type"] == "licitacao"
            assert results[0]["content"] == "Texto de exemplo"
            assert results[0]["similarity"] == 0.95
            assert results[1]["source_type"] == "contrato"

            mock_provider.embed.assert_awaited_once_with(["busca"])
            session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_empty_embeddings_returns_empty(self):
        mock_provider = AsyncMock()
        mock_provider.embed.return_value = []

        session = AsyncMock()

        with patch("shared.ai.rag.get_llm_provider", return_value=mock_provider):
            results = await retrieve_context("query", session)
            assert results == []
            session.execute.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_no_results_from_db(self):
        mock_provider = AsyncMock()
        mock_provider.embed.return_value = [[0.1, 0.2]]

        mock_result = MagicMock()
        mock_result.fetchall.return_value = []

        session = AsyncMock()
        session.execute.return_value = mock_result

        with patch("shared.ai.rag.get_llm_provider", return_value=mock_provider):
            results = await retrieve_context("query", session)
            assert results == []

    @pytest.mark.asyncio
    async def test_vec_str_format(self):
        mock_provider = AsyncMock()
        mock_provider.embed.return_value = [[1.5, -0.3, 0.0]]

        mock_result = MagicMock()
        mock_result.fetchall.return_value = []

        session = AsyncMock()
        session.execute.return_value = mock_result

        with patch("shared.ai.rag.get_llm_provider", return_value=mock_provider):
            await retrieve_context("test", session)
            call_args = session.execute.call_args
            params = call_args[0][1]
            assert params["query_vec"] == "[1.5,-0.3,0.0]"
            assert params["limit"] == 5
