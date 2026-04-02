from openwatch_ai.provider import get_llm_provider
from openwatch_config.settings import settings


async def classify_text(text: str, categories: list[str]) -> str:
    """Classify a procurement description into a category.

    Uses LLM when available, falls back to keyword matching.
    """
    if settings.LLM_PROVIDER == "none":
        return _keyword_classify(text, categories)

    provider = get_llm_provider()
    prompt = (
        f"Classifique o seguinte texto de licitação em uma das categorias: "
        f"{', '.join(categories)}.\n\nTexto: {text}\n\n"
        f"Responda apenas com o nome da categoria."
    )
    result = await provider.complete(prompt)
    result = result.strip()
    # Validate response is one of the categories
    for cat in categories:
        if cat.lower() in result.lower():
            return cat
    return categories[0] if categories else "outros"


def _keyword_classify(text: str, categories: list[str]) -> str:
    """Simple keyword-based classification fallback."""
    text_lower = text.lower()
    for cat in categories:
        if cat.lower() in text_lower:
            return cat
    return categories[0] if categories else "outros"


async def semantic_cluster(
    texts: list[str], min_cluster_size: int = 3, eps: float = 0.3
) -> list[list[int]]:
    """Cluster texts by semantic similarity using DBSCAN on embeddings.

    Returns list of clusters, each a list of text indices.
    """
    if len(texts) < min_cluster_size:
        return [list(range(len(texts)))]

    provider = get_llm_provider()
    embeddings = await provider.embed(texts)

    # Simple distance-based clustering (DBSCAN-like)
    n = len(embeddings)
    visited = [False] * n
    clusters: list[list[int]] = []

    def _cosine_sim(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    for i in range(n):
        if visited[i]:
            continue
        cluster = [i]
        visited[i] = True
        for j in range(i + 1, n):
            if visited[j]:
                continue
            sim = _cosine_sim(embeddings[i], embeddings[j])
            if sim >= (1 - eps):
                cluster.append(j)
                visited[j] = True
        if len(cluster) >= min_cluster_size:
            clusters.append(cluster)

    # Assign unclustered items to noise cluster
    unclustered = [i for i in range(n) if not any(i in c for c in clusters)]
    if unclustered:
        clusters.append(unclustered)

    return clusters
