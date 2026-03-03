import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shared.ai.provider import NoOpProvider, get_llm_provider


class TestNoOpProvider:
    @pytest.mark.asyncio
    async def test_complete_returns_fallback(self):
        provider = NoOpProvider()
        result = await provider.complete("test prompt")
        assert "determinística" in result
        assert "LLM desabilitado" in result

    @pytest.mark.asyncio
    async def test_complete_with_system(self):
        provider = NoOpProvider()
        result = await provider.complete("prompt", system="system")
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_embed_returns_zero_vectors(self):
        provider = NoOpProvider()
        result = await provider.embed(["text1", "text2"])
        assert len(result) == 2
        assert len(result[0]) == 1536
        assert all(v == 0.0 for v in result[0])

    @pytest.mark.asyncio
    async def test_embed_empty(self):
        provider = NoOpProvider()
        result = await provider.embed([])
        assert result == []


class TestGetLlmProvider:
    def test_none_provider(self):
        provider = get_llm_provider()
        assert isinstance(provider, NoOpProvider)

    @patch.dict(os.environ, {"LLM_PROVIDER": "openai", "OPENAI_API_KEY": "test-key"})
    def test_openai_provider(self):
        from shared.ai.provider import OpenAIProvider
        assert OpenAIProvider is not None

    def test_get_llm_provider_openai(self):
        with patch("shared.ai.provider.settings") as mock_settings, \
             patch.dict("sys.modules", {"openai": MagicMock()}):
            mock_settings.LLM_PROVIDER = "openai"
            mock_settings.OPENAI_API_KEY = "sk-test"

            from shared.ai.provider import OpenAIProvider
            provider = get_llm_provider()
            assert isinstance(provider, OpenAIProvider)

    def test_anthropic_provider(self):
        with patch("shared.ai.provider.settings") as mock_settings, \
             patch.dict("sys.modules", {"anthropic": MagicMock()}):
            mock_settings.LLM_PROVIDER = "anthropic"
            mock_settings.ANTHROPIC_API_KEY = "sk-ant-test"

            from shared.ai.provider import AnthropicProvider
            provider = get_llm_provider()
            assert isinstance(provider, AnthropicProvider)


class TestOpenAIProvider:
    def _make_provider(self, mock_client):
        """Create an OpenAIProvider with a mocked openai module."""
        mock_openai_mod = MagicMock()
        mock_openai_mod.AsyncOpenAI.return_value = mock_client

        with patch.dict("sys.modules", {"openai": mock_openai_mod}), \
             patch("shared.ai.provider.settings") as mock_settings:
            mock_settings.OPENAI_API_KEY = "sk-test"
            mock_settings.OPENAI_MODEL = "gpt-4o-mini"
            mock_settings.EMBEDDING_MODEL = "text-embedding-3-small"

            from shared.ai.provider import OpenAIProvider
            provider = OpenAIProvider()
            return provider, mock_settings

    def test_init(self):
        mock_client = MagicMock()
        provider, _ = self._make_provider(mock_client)
        assert provider.client is mock_client

    @pytest.mark.asyncio
    async def test_complete_without_system(self):
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "test response"
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response

        provider, mock_settings = self._make_provider(mock_client)

        result = await provider.complete("test prompt")
        assert result == "test response"
        call_args = mock_client.chat.completions.create.call_args
        messages = call_args.kwargs["messages"]
        assert len(messages) == 1
        assert messages[0]["role"] == "user"

    @pytest.mark.asyncio
    async def test_complete_with_system(self):
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "response with system"
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response

        provider, _ = self._make_provider(mock_client)

        result = await provider.complete("prompt", system="sys")
        assert result == "response with system"
        call_args = mock_client.chat.completions.create.call_args
        messages = call_args.kwargs["messages"]
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"

    @pytest.mark.asyncio
    async def test_complete_none_content(self):
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = None
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response

        provider, _ = self._make_provider(mock_client)

        result = await provider.complete("prompt")
        assert result == ""

    @pytest.mark.asyncio
    async def test_embed(self):
        mock_client = AsyncMock()
        item1 = MagicMock()
        item1.embedding = [0.1, 0.2, 0.3]
        item2 = MagicMock()
        item2.embedding = [0.4, 0.5, 0.6]
        mock_response = MagicMock()
        mock_response.data = [item1, item2]
        mock_client.embeddings.create.return_value = mock_response

        provider, _ = self._make_provider(mock_client)

        result = await provider.embed(["hello", "world"])
        assert result == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        mock_client.embeddings.create.assert_called_once_with(
            model="text-embedding-3-small", input=["hello", "world"]
        )


class TestAnthropicProvider:
    """Tests for the AnthropicProvider class."""

    def _make_provider(self, mock_anthropic_client):
        """Create an AnthropicProvider with a mocked anthropic module."""
        mock_anthropic_mod = MagicMock()
        mock_anthropic_mod.AsyncAnthropic.return_value = mock_anthropic_client

        with patch.dict("sys.modules", {"anthropic": mock_anthropic_mod}), \
             patch("shared.ai.provider.settings") as mock_settings:
            mock_settings.ANTHROPIC_API_KEY = "sk-ant-test"
            mock_settings.ANTHROPIC_MODEL = "claude-sonnet-4-6"
            mock_settings.OPENAI_API_KEY = ""
            mock_settings.EMBEDDING_MODEL = "text-embedding-3-small"

            from shared.ai.provider import AnthropicProvider
            provider = AnthropicProvider()
            return provider, mock_settings

    @pytest.mark.asyncio
    async def test_complete_without_system(self):
        mock_client = AsyncMock()
        mock_content_block = MagicMock()
        mock_content_block.text = "anthropic response"
        mock_response = MagicMock()
        mock_response.content = [mock_content_block]
        mock_client.messages.create.return_value = mock_response

        provider, _ = self._make_provider(mock_client)

        result = await provider.complete("test prompt")
        assert result == "anthropic response"
        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["system"] == "You are a helpful assistant."
        assert call_kwargs["messages"] == [{"role": "user", "content": "test prompt"}]

    @pytest.mark.asyncio
    async def test_complete_with_system(self):
        mock_client = AsyncMock()
        mock_content_block = MagicMock()
        mock_content_block.text = "response with custom system"
        mock_response = MagicMock()
        mock_response.content = [mock_content_block]
        mock_client.messages.create.return_value = mock_response

        provider, _ = self._make_provider(mock_client)

        result = await provider.complete("prompt", system="custom system")
        assert result == "response with custom system"
        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["system"] == "custom system"

    @pytest.mark.asyncio
    async def test_embed_with_openai_key(self):
        mock_anthropic_client = AsyncMock()
        mock_openai_client = AsyncMock()

        item1 = MagicMock()
        item1.embedding = [0.1, 0.2, 0.3]
        mock_embed_response = MagicMock()
        mock_embed_response.data = [item1]
        mock_openai_client.embeddings.create.return_value = mock_embed_response

        mock_openai_mod = MagicMock()
        mock_openai_mod.AsyncOpenAI.return_value = mock_openai_client

        provider, mock_settings = self._make_provider(mock_anthropic_client)
        # Must set OPENAI_API_KEY on the shared settings object that embed() reads
        with patch("shared.ai.provider.settings") as live_settings, \
             patch.dict("sys.modules", {"openai": mock_openai_mod}):
            live_settings.OPENAI_API_KEY = "sk-test-openai"
            live_settings.EMBEDDING_MODEL = "text-embedding-3-small"
            result = await provider.embed(["hello"])

        assert result == [[0.1, 0.2, 0.3]]
        mock_openai_client.embeddings.create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_embed_without_openai_key(self):
        from unittest.mock import patch
        mock_anthropic_client = AsyncMock()
        provider, _ = self._make_provider(mock_anthropic_client)

        with patch("shared.ai.provider.settings") as mock_settings:
            mock_settings.OPENAI_API_KEY = ""
            result = await provider.embed(["text1", "text2"])

        assert len(result) == 2
        assert len(result[0]) == 1536
        assert all(v == 0.0 for v in result[0])
        assert all(v == 0.0 for v in result[1])

    @pytest.mark.asyncio
    async def test_embed_empty_texts(self):
        from unittest.mock import patch
        mock_anthropic_client = AsyncMock()
        provider, _ = self._make_provider(mock_anthropic_client)

        with patch("shared.ai.provider.settings") as mock_settings:
            mock_settings.OPENAI_API_KEY = ""
            result = await provider.embed([])
        assert result == []
