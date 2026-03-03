from sqlalchemy.ext.asyncio import AsyncSession

from shared.ai.provider import get_llm_provider


async def embed_texts(
    texts: list[str],
    source_type: str,
    source_ids: list[str],
    session: AsyncSession,
) -> None:
    """Embed texts and store in text_embedding table with pgvector.

    1. Create text_corpus entries for each text.
    2. Generate embeddings via the configured LLM provider.
    3. Store embeddings in text_embedding linked to corpus entries.
    """
    if not texts:
        return

    provider = get_llm_provider()
    embeddings = await provider.embed(texts)

    from shared.models.orm import TextCorpus, TextEmbedding
    from shared.config import settings

    for text, source_id, embedding in zip(texts, source_ids, embeddings):
        corpus = TextCorpus(
            source_type=source_type,
            source_id=source_id,
            content=text,
        )
        session.add(corpus)
        await session.flush()

        text_emb = TextEmbedding(
            corpus_id=corpus.id,
            model=settings.EMBEDDING_MODEL,
            embedding=embedding,
        )
        session.add(text_emb)

    await session.commit()
