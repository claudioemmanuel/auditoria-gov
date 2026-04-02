from unittest.mock import AsyncMock, patch

import pytest

from openwatch_ai.classify import classify_text, _keyword_classify, semantic_cluster


class TestKeywordClassify:
    def test_matching_category(self):
        result = _keyword_classify("material de escritório", ["escritório", "informática"])
        assert result == "escritório"

    def test_first_match_wins(self):
        result = _keyword_classify("material de escritório para informática", ["escritório", "informática"])
        assert result == "escritório"

    def test_no_match_returns_first(self):
        result = _keyword_classify("alimento", ["escritório", "informática"])
        assert result == "escritório"

    def test_empty_categories(self):
        result = _keyword_classify("test", [])
        assert result == "outros"

    def test_case_insensitive(self):
        result = _keyword_classify("ESCRITÓRIO", ["escritório"])
        assert result == "escritório"


class TestClassifyText:
    @pytest.mark.asyncio
    async def test_fallback_to_keyword(self):
        """With LLM_PROVIDER=none, uses keyword classify."""
        result = await classify_text(
            "material de escritório para uso interno",
            ["escritório", "informática", "serviço"],
        )
        assert result == "escritório"

    @pytest.mark.asyncio
    async def test_empty_categories(self):
        result = await classify_text("test", [])
        assert result == "outros"


class TestSemanticCluster:
    @pytest.mark.asyncio
    async def test_small_input_single_cluster(self):
        result = await semantic_cluster(["a", "b"], min_cluster_size=3)
        assert len(result) == 1
        assert result[0] == [0, 1]

    @pytest.mark.asyncio
    async def test_returns_clusters(self):
        """With NoOp provider (zero vectors), all texts are identical → one cluster."""
        texts = ["text " + str(i) for i in range(5)]
        result = await semantic_cluster(texts, min_cluster_size=3, eps=0.3)
        assert len(result) >= 1
        # All indices should appear somewhere
        all_indices = set()
        for cluster in result:
            all_indices.update(cluster)
        assert all_indices == {0, 1, 2, 3, 4}

    @pytest.mark.asyncio
    async def test_empty_input(self):
        result = await semantic_cluster([], min_cluster_size=3)
        assert result == [[]]

    @pytest.mark.asyncio
    async def test_single_item(self):
        result = await semantic_cluster(["one"], min_cluster_size=3)
        assert result == [[0]]


class TestClassifyTextWithLLM:
    @pytest.mark.asyncio
    async def test_llm_returns_matching_category(self):
        mock_provider = AsyncMock()
        mock_provider.complete.return_value = "  informática  "

        with patch("shared.ai.classify.settings") as mock_settings, \
             patch("shared.ai.classify.get_llm_provider", return_value=mock_provider):
            mock_settings.LLM_PROVIDER = "openai"

            result = await classify_text(
                "computador desktop", ["escritório", "informática", "serviço"]
            )
            assert result == "informática"
            mock_provider.complete.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_llm_returns_no_match_falls_back_to_first(self):
        mock_provider = AsyncMock()
        mock_provider.complete.return_value = "não sei"

        with patch("shared.ai.classify.settings") as mock_settings, \
             patch("shared.ai.classify.get_llm_provider", return_value=mock_provider):
            mock_settings.LLM_PROVIDER = "openai"

            result = await classify_text(
                "xyz", ["escritório", "informática"]
            )
            assert result == "escritório"

    @pytest.mark.asyncio
    async def test_llm_empty_categories(self):
        mock_provider = AsyncMock()
        mock_provider.complete.return_value = "nada"

        with patch("shared.ai.classify.settings") as mock_settings, \
             patch("shared.ai.classify.get_llm_provider", return_value=mock_provider):
            mock_settings.LLM_PROVIDER = "openai"

            result = await classify_text("xyz", [])
            assert result == "outros"


class TestSemanticClusterWithRealEmbeddings:
    @pytest.mark.asyncio
    async def test_clustering_with_similar_vectors(self):
        """Mock provider returns non-zero vectors to test actual clustering logic."""
        mock_provider = AsyncMock()
        # 5 vectors: first 3 are similar, last 2 are similar but different from first 3
        mock_provider.embed.return_value = [
            [1.0, 0.0, 0.0],
            [0.99, 0.01, 0.0],
            [0.98, 0.02, 0.0],
            [0.0, 1.0, 0.0],
            [0.01, 0.99, 0.0],
        ]

        with patch("shared.ai.classify.get_llm_provider", return_value=mock_provider):
            result = await semantic_cluster(
                ["a", "b", "c", "d", "e"], min_cluster_size=2, eps=0.1
            )
            # Should have at least one cluster with items 0,1,2 and one with 3,4
            all_indices = set()
            for cluster in result:
                all_indices.update(cluster)
            assert all_indices == {0, 1, 2, 3, 4}

    @pytest.mark.asyncio
    async def test_cosine_sim_normal_path(self):
        """Cover the normal cosine similarity return (non-zero vectors)."""
        mock_provider = AsyncMock()
        # Identical vectors — cosine similarity = 1.0
        mock_provider.embed.return_value = [
            [1.0, 0.0],
            [1.0, 0.0],
            [1.0, 0.0],
        ]

        with patch("shared.ai.classify.get_llm_provider", return_value=mock_provider):
            result = await semantic_cluster(
                ["x", "y", "z"], min_cluster_size=3, eps=0.3
            )
            # All items identical, should form one cluster
            assert len(result) == 1
            assert sorted(result[0]) == [0, 1, 2]

    @pytest.mark.asyncio
    async def test_visited_j_skip_path(self):
        """Cover visited[j] continue (line 70).

        Item 0 and 2 are similar → 2 gets clustered with 0.
        When i=1, j=2 → visited[2] is True → continue.
        """
        mock_provider = AsyncMock()
        mock_provider.embed.return_value = [
            [1.0, 0.0],   # 0: similar to 2
            [0.0, 1.0],   # 1: different from 0 and 2
            [0.99, 0.01], # 2: similar to 0, gets visited when i=0
        ]

        with patch("shared.ai.classify.get_llm_provider", return_value=mock_provider):
            result = await semantic_cluster(
                ["a", "b", "c"], min_cluster_size=2, eps=0.3
            )
            all_indices = set()
            for cluster in result:
                all_indices.update(cluster)
            assert all_indices == {0, 1, 2}
