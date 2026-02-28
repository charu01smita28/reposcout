from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from mistralai import Mistral
from backend.config import QDRANT_PATH, QDRANT_COLLECTION, EMBEDDING_DIM, MISTRAL_API_KEY

_client: QdrantClient | None = None
_mistral: Mistral | None = None


def get_client() -> QdrantClient:
    global _client
    if _client is None:
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
    client = get_client()
    query_embedding = get_embedding(query)
    results = client.search(
        collection_name=QDRANT_COLLECTION,
        query_vector=query_embedding,
        limit=limit,
        score_threshold=score_threshold,
    )
    return [
        {
            "name": hit.payload.get("name", ""),
            "description": hit.payload.get("description", ""),
            "stars": hit.payload.get("stars", 0),
            "dependents_count": hit.payload.get("dependents_count", 0),
            "score": hit.score,
        }
        for hit in results
    ]


def upsert_packages(points: list[PointStruct], batch_size: int = 100):
    client = get_client()
    ensure_collection()
    for i in range(0, len(points), batch_size):
        batch = points[i : i + batch_size]
        client.upsert(collection_name=QDRANT_COLLECTION, points=batch)
