from typing import Protocol

from shared.config import settings


class LLMProvider(Protocol):
    """Protocol for LLM providers."""

    async def complete(self, prompt: str, system: str = "") -> str: ...
    async def embed(self, texts: list[str]) -> list[list[float]]: ...


class OpenAIProvider:
    """OpenAI-backed LLM provider."""

    def __init__(self) -> None:
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def complete(self, prompt: str, system: str = "") -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = await self.client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=messages,
            temperature=0.2,
            max_tokens=2000,
        )
        return response.choices[0].message.content or ""

    async def embed(self, texts: list[str]) -> list[list[float]]:
        response = await self.client.embeddings.create(
            model=settings.EMBEDDING_MODEL,
            input=texts,
        )
        return [item.embedding for item in response.data]


class AnthropicProvider:
    """Anthropic Claude-backed LLM provider.

    Uses Anthropic's messages API for completions.
    Delegates embeddings to OpenAI (Anthropic has no embeddings API).
    """

    def __init__(self) -> None:
        import anthropic
        self.client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    async def complete(self, prompt: str, system: str = "") -> str:
        response = await self.client.messages.create(
            model=settings.ANTHROPIC_MODEL,
            max_tokens=2000,
            system=system or "You are a helpful assistant.",
            messages=[{"role": "user", "content": prompt}],
        )
        content = response.content[0]
        return content.text if hasattr(content, "text") else ""

    async def embed(self, texts: list[str]) -> list[list[float]]:
        # Anthropic has no embeddings API — delegate to OpenAI.
        if settings.OPENAI_API_KEY:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            response = await client.embeddings.create(
                model=settings.EMBEDDING_MODEL,
                input=texts,
            )
            return [item.embedding for item in response.data]
        # Fallback: zero vectors (no-op, embeddings disabled)
        return [[0.0] * 1536 for _ in texts]


class NoOpProvider:
    """Deterministic fallback — uses Jinja2 templates instead of LLM."""

    async def complete(self, prompt: str, system: str = "") -> str:
        return (
            "**Explicação determinística (LLM desabilitado)**\n\n"
            "Este sinal de risco foi gerado automaticamente com base em "
            "critérios estatísticos. Para uma análise detalhada com linguagem "
            "natural, ative o provedor de LLM na configuração."
        )

    async def embed(self, texts: list[str]) -> list[list[float]]:
        # Return zero vectors as placeholder
        return [[0.0] * 1536 for _ in texts]


def get_llm_provider() -> LLMProvider:
    """Factory for LLM providers based on config."""
    if settings.LLM_PROVIDER == "openai":
        return OpenAIProvider()
    if settings.LLM_PROVIDER == "anthropic":
        return AnthropicProvider()
    return NoOpProvider()
