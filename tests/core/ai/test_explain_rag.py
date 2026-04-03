"""Tests for explain_signal with RAG context integration.

Covers:
- No RAG when session=None
- RAG context added when session provided
- Empty RAG context fallback
- Deterministic path unchanged regardless of session
"""

from unittest.mock import AsyncMock, patch

import pytest

from openwatch_ai.explain import explain_signal


_BASE_KWARGS = {
    "typology_code": "T01",
    "typology_name": "Concentracao em Fornecedor",
    "severity": "high",
    "confidence": 0.85,
    "title": "Alta concentracao no orgao X",
    "factors": {"hhi": 0.95},
    "evidence_refs": [{"description": "Dados de licitacoes 2023"}],
}


class TestExplainSignalWithRAG:
    @pytest.mark.asyncio
    async def test_no_rag_when_no_session(self):
        """session=None: build_rag_context NOT called, prompt still rendered."""
        mock_provider = AsyncMock()
        mock_provider.complete.return_value = "LLM explanation"

        with patch("shared.ai.explain.settings") as mock_settings, \
             patch("shared.ai.explain.get_llm_provider", return_value=mock_provider), \
             patch("shared.ai.rag.build_rag_context") as mock_rag:
            mock_settings.LLM_PROVIDER = "openai"

            result = await explain_signal(**_BASE_KWARGS, session=None)

        assert result == "LLM explanation"
        mock_rag.assert_not_called()
        mock_provider.complete.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_rag_context_added_when_session_provided(self):
        """Mock session + build_rag_context: rag_context appears in rendered prompt."""
        mock_session = AsyncMock()
        mock_provider = AsyncMock()
        mock_provider.complete.return_value = "LLM explanation with RAG"

        rag_text = "[1] Fonte: signal/abc (similaridade: 0.92)\nHistorical signal text"

        # build_rag_context is imported lazily: from openwatch_ai.rag import build_rag_context
        # So we patch at the source module level.
        with patch("shared.ai.explain.settings") as mock_settings, \
             patch("shared.ai.explain.get_llm_provider", return_value=mock_provider), \
             patch("shared.ai.rag.build_rag_context", new_callable=AsyncMock, return_value=rag_text) as mock_rag:
            mock_settings.LLM_PROVIDER = "openai"

            result = await explain_signal(**_BASE_KWARGS, session=mock_session)

        assert result == "LLM explanation with RAG"
        mock_rag.assert_awaited_once_with("Alta concentracao no orgao X", mock_session, max_tokens=500)

        # Verify the prompt sent to LLM contains the RAG context
        prompt_arg = mock_provider.complete.call_args[0][0]
        assert "Historical signal text" in prompt_arg
        assert "Sinais Similares" in prompt_arg

    @pytest.mark.asyncio
    async def test_rag_context_empty_string_fallback(self):
        """build_rag_context returns empty string: template still renders (rag block hidden)."""
        mock_session = AsyncMock()
        mock_provider = AsyncMock()
        mock_provider.complete.return_value = "LLM explanation no RAG block"

        with patch("shared.ai.explain.settings") as mock_settings, \
             patch("shared.ai.explain.get_llm_provider", return_value=mock_provider), \
             patch("shared.ai.rag.build_rag_context", new_callable=AsyncMock, return_value=""):
            mock_settings.LLM_PROVIDER = "openai"

            result = await explain_signal(**_BASE_KWARGS, session=mock_session)

        assert result == "LLM explanation no RAG block"
        # Prompt should NOT contain "Sinais Similares" since rag_context is empty
        prompt_arg = mock_provider.complete.call_args[0][0]
        assert "Sinais Similares" not in prompt_arg

    @pytest.mark.asyncio
    async def test_deterministic_path_unchanged(self):
        """LLM_PROVIDER=none: returns deterministic template regardless of session."""
        mock_session = AsyncMock()

        # No need to patch LLM_PROVIDER -- conftest sets it to "none" by default
        result = await explain_signal(**_BASE_KWARGS, session=mock_session)

        # Deterministic template markers
        assert "indicador estatistico" in result.lower() or "indicador estatístico" in result.lower()
        assert "T01" in result
        assert "Concentracao em Fornecedor" in result
