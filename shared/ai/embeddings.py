from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.ai.provider import get_llm_provider


async def embed_entity(
    session: AsyncSession,
    entity_id: object,
    name_normalized: str,
) -> None:
    """Embed entity normalized name and upsert into text_embedding.

    Skips silently if name_normalized is empty.
    Re-embeds if the stored content has changed (name update).
    """
    from shared.config import settings
    from shared.models.orm import TextCorpus, TextEmbedding

    if not name_normalized:
        return

    source_id = str(entity_id)

    corpus_stmt = select(TextCorpus).where(
        TextCorpus.source_type == "entity",
        TextCorpus.source_id == source_id,
    ).limit(1)
    corpus = (await session.execute(corpus_stmt)).scalar_one_or_none()

    if corpus is None:
        corpus = TextCorpus(
            source_type="entity",
            source_id=source_id,
            content=name_normalized,
        )
        session.add(corpus)
        await session.flush()
    elif corpus.content != name_normalized:
        corpus.content = name_normalized
        # Remove stale embedding so it gets regenerated below.
        old_emb_stmt = select(TextEmbedding).where(TextEmbedding.corpus_id == corpus.id)
        old_emb = (await session.execute(old_emb_stmt)).scalar_one_or_none()
        if old_emb is not None:
            await session.delete(old_emb)
        await session.flush()

    emb_stmt = select(TextEmbedding).where(TextEmbedding.corpus_id == corpus.id)
    if (await session.execute(emb_stmt)).scalar_one_or_none() is not None:
        return  # Already embedded and up-to-date.

    provider = get_llm_provider()
    embeddings = await provider.embed([name_normalized])
    if not embeddings:
        return

    session.add(TextEmbedding(
        corpus_id=corpus.id,
        model=settings.EMBEDDING_MODEL,
        embedding=embeddings[0],
    ))
    await session.flush()


async def embed_signal_summary(
    session: AsyncSession,
    signal_id: object,
    summary_text: str,
) -> None:
    """Embed signal summary text and upsert into text_embedding.

    Skips silently if summary_text is empty.
    No re-embed on update — signal summaries are immutable after creation.
    """
    from shared.config import settings
    from shared.models.orm import TextCorpus, TextEmbedding

    if not summary_text:
        return

    source_id = str(signal_id)

    corpus_stmt = select(TextCorpus).where(
        TextCorpus.source_type == "signal",
        TextCorpus.source_id == source_id,
    ).limit(1)
    corpus = (await session.execute(corpus_stmt)).scalar_one_or_none()

    if corpus is None:
        corpus = TextCorpus(
            source_type="signal",
            source_id=source_id,
            content=summary_text,
        )
        session.add(corpus)
        await session.flush()

    emb_stmt = select(TextEmbedding).where(TextEmbedding.corpus_id == corpus.id)
    if (await session.execute(emb_stmt)).scalar_one_or_none() is not None:
        return  # Already embedded.

    provider = get_llm_provider()
    embeddings = await provider.embed([summary_text])
    if not embeddings:
        return

    session.add(TextEmbedding(
        corpus_id=corpus.id,
        model=settings.EMBEDDING_MODEL,
        embedding=embeddings[0],
    ))
    await session.flush()


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
