import logging

from qdrant_client import QdrantClient, models
from qdrant_client.models import Distance, VectorParams, PointStruct
from mistralai import Mistral
from backend.config import QDRANT_PATH, QDRANT_URL, QDRANT_API_KEY, QDRANT_COLLECTION, EMBEDDING_DIM, MISTRAL_API_KEY
from backend.models import SemanticSearchResult

logger = logging.getLogger(__name__)

_client: QdrantClient | None = None
_mistral: Mistral | None = None


def get_client() -> QdrantClient:
    global _client
    if _client is None:
        if QDRANT_URL:
            _client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY or None)
        else:
            _client = QdrantClient(path=QDRANT_PATH)
    return _client


def get_mistral() -> Mistral:
    global _mistral
    if _mistral is None:
        _mistral = Mistral(api_key=MISTRAL_API_KEY)
    return _mistral


def ensure_collection():
    client = get_client()
    collections = [c.name for c in client.get_collections().collections]
    if QDRANT_COLLECTION not in collections:
        client.create_collection(
            collection_name=QDRANT_COLLECTION,
            vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
        )


def get_embedding(text: str) -> list[float]:
    mistral = get_mistral()
    response = mistral.embeddings.create(model="mistral-embed", inputs=[text])
    return response.data[0].embedding


def get_embeddings_batch(texts: list[str]) -> list[list[float]]:
    mistral = get_mistral()
    response = mistral.embeddings.create(model="mistral-embed", inputs=texts)
    return [item.embedding for item in response.data]


def semantic_search_packages(query: str, limit: int = 20, score_threshold: float = 0.3) -> list[dict]:
    """Search Qdrant for packages matching the query.
    Filters out junk (0 stars AND 0 dependents AND 0 growth).
    Returns lean results (QdrantPayload fields + similarity_score).
    For full data, caller should enrich from DuckDB by package name."""
    client = get_client()
    query_embedding = get_embedding(query)

    # Fetch extra results, then post-filter junk and re-rank by quality
    fetch_limit = limit * 10
    response = client.query_points(
        collection_name=QDRANT_COLLECTION,
        query=query_embedding,
        limit=fetch_limit,
        score_threshold=score_threshold,
    )

    results = []
    for hit in response.points:
        stars = hit.payload.get("stars", 0) or 0
        deps = hit.payload.get("dependent_count", 0) or 0
        growth = hit.payload.get("growth_pct", 0) or 0

        # Skip junk: need real adoption — 100+ dependents minimum
        if deps < 100:
            continue

        # Blend: semantic similarity + popularity boost
        popularity = min((stars + deps * 10) / 10000, 1.0)
        growth_boost = min(growth / 1000, 0.5) if growth > 0 else 0
        blended_score = hit.score * 0.6 + popularity * 0.25 + growth_boost * 0.15

        results.append(
            (
                blended_score,
                SemanticSearchResult(
                    name=hit.payload.get("name", ""),
                    summary=hit.payload.get("summary", ""),
                    stars=stars,
                    dependent_count=deps,
                    growth_pct=growth,
                    version=hit.payload.get("version", ""),
                    similarity_score=hit.score,
                ).model_dump(),
            )
        )

    # Sort by blended score, return top `limit`
    results.sort(key=lambda x: x[0], reverse=True)
    final = [r[1] for r in results[:limit]]

    # Log top 10 for debugging
    logger.info("Qdrant search: %r → %d results (from %d raw)", query, len(final), len(response.points))
    for i, pkg in enumerate(final[:10]):
        logger.info(
            "  #%d %-30s  stars=%-6s deps=%-6s growth=%-6s%% sim=%.3f",
            i + 1,
            pkg["name"],
            pkg["stars"],
            pkg["dependent_count"],
            pkg["growth_pct"],
            pkg["similarity_score"],
        )

    return final


def upsert_packages(points: list[PointStruct], batch_size: int = 100):
    client = get_client()
    ensure_collection()
    for i in range(0, len(points), batch_size):
        batch = points[i : i + batch_size]
        client.upsert(collection_name=QDRANT_COLLECTION, points=batch)
