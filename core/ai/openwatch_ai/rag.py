"""Retrieval-Augmented Generation (RAG) module.

Uses pgvector HNSW index on text_embedding table for semantic search.
Provides context retrieval for LLM-based analysis and explanations.
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from openwatch_ai.provider import get_llm_provider


async def retrieve_context(
    query: str, session: AsyncSession, limit: int = 5
) -> list[dict]:
    """Cosine similarity search on text_embedding for RAG context.

    Returns top-k most similar text corpus entries with their scores.
    """
    provider = get_llm_provider()
    query_embeddings = await provider.embed([query])
    if not query_embeddings:
        return []

    query_vec = query_embeddings[0]
    vec_str = "[" + ",".join(str(v) for v in query_vec) + "]"

    sql = text("""
        SELECT
            tc.id,
            tc.source_type,
            tc.source_id,
            tc.content,
            1 - (te.embedding <=> :query_vec::vector) AS similarity
        FROM text_embedding te
        JOIN text_corpus tc ON tc.id = te.corpus_id
        ORDER BY te.embedding <=> :query_vec::vector
        LIMIT :limit
    """)

    result = await session.execute(sql, {"query_vec": vec_str, "limit": limit})
    rows = result.fetchall()

    return [
        {
            "id": str(row.id),
            "source_type": row.source_type,
            "source_id": row.source_id,
            "content": row.content,
            "similarity": float(row.similarity),
        }
        for row in rows
    ]


async def search_similar_texts(
    query_embedding: list[float],
    session: AsyncSession,
    top_k: int = 10,
    min_similarity: float = 0.5,
) -> list[dict]:
    """Search for similar texts using a pre-computed embedding.

    Uses pgvector HNSW index for efficient nearest-neighbor search.
    Returns texts above min_similarity threshold.
    """
    vec_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

    sql = text("""
        SELECT
            tc.id,
            tc.source_type,
            tc.source_id,
            tc.content,
            tc.attrs,
            1 - (te.embedding <=> :query_vec::vector) AS similarity
        FROM text_embedding te
        JOIN text_corpus tc ON tc.id = te.corpus_id
        WHERE 1 - (te.embedding <=> :query_vec::vector) >= :min_sim
        ORDER BY te.embedding <=> :query_vec::vector
        LIMIT :top_k
    """)

    result = await session.execute(
        sql,
        {"query_vec": vec_str, "top_k": top_k, "min_sim": min_similarity},
    )
    rows = result.fetchall()

    return [
        {
            "id": str(row.id),
            "source_type": row.source_type,
            "source_id": row.source_id,
            "content": row.content[:500],  # Truncate for context window
            "attrs": row.attrs,
            "similarity": float(row.similarity),
        }
        for row in rows
    ]


async def build_rag_context(
    query: str,
    session: AsyncSession,
    max_tokens: int = 2000,
) -> str:
    """Build a RAG context string from similar texts for LLM prompts.

    Retrieves relevant documents and formats them as numbered context blocks.
    """
    docs = await retrieve_context(query, session, limit=5)

    if not docs:
        return ""

    context_parts: list[str] = []
    total_len = 0

    for i, doc in enumerate(docs, 1):
        content = doc["content"]
        # Rough token estimate: 1 token ≈ 4 chars
        if total_len + len(content) // 4 > max_tokens:
            content = content[: (max_tokens - total_len) * 4]

        block = (
            f"[{i}] Fonte: {doc['source_type']}/{doc['source_id']} "
            f"(similaridade: {doc['similarity']:.2f})\n{content}"
        )
        context_parts.append(block)
        total_len += len(content) // 4

        if total_len >= max_tokens:
            break

    return "\n\n".join(context_parts)
