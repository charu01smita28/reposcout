"""
Embed packages that are in DuckDB but missing from Qdrant.

Usage:
    python scripts/embed_missing.py
"""

import sys
import time
import duckdb
from pathlib import Path
from tqdm import tqdm
from qdrant_client.models import PointStruct

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "scripts"))

from backend.config import QDRANT_COLLECTION, EMBEDDING_DIM
from backend.models import QdrantPayload
from backend.utils.qdrant_client import get_client, get_embeddings_batch, ensure_collection
from text_cleaner import build_embedding_text

DB_PATH = BASE_DIR / "data" / "reposcout.db"
BATCH_SIZE = 25


def get_qdrant_names() -> set[str]:
    """Get all package names already in Qdrant."""
    client = get_client()
    names = set()
    offset = None

    while True:
        result = client.scroll(
            collection_name=QDRANT_COLLECTION,
            limit=1000,
            offset=offset,
            with_payload=["name"],
            with_vectors=False,
        )
        points, next_offset = result
        for p in points:
            name = p.payload.get("name", "")
            if name:
                names.add(name.lower())
        if next_offset is None:
            break
        offset = next_offset

    return names


def get_missing_packages(existing_names: set[str]) -> list[dict]:
    """Get packages from DuckDB that are NOT in Qdrant.
    Joins packages + pypi_metadata, filters out packages already indexed."""
    ...  # DuckDB query + diff logic removed for public repository
    return []


def embed_packages(packages: list[dict]):
    """Embed and upsert missing packages into Qdrant."""
    client = get_client()
    ensure_collection()

    # Get current max ID to avoid collisions
    info = client.get_collection(QDRANT_COLLECTION)
    next_id = info.points_count

    indexed = 0
    errors = 0
    pbar = tqdm(total=len(packages), desc="Embedding missing", unit="pkg", ncols=90)

    for i in range(0, len(packages), BATCH_SIZE):
        batch = packages[i : i + BATCH_SIZE]
        texts = [build_embedding_text(pkg) for pkg in batch]

        try:
            embeddings = get_embeddings_batch(texts)
        except Exception as e:
            ...  # Rate limit handling + retry logic removed for public repository
            errors += len(batch)
            pbar.update(len(batch))
            continue

        points = []
        for j, (pkg, embedding) in enumerate(zip(batch, embeddings)):
            payload = QdrantPayload(
                name=pkg.get("package_name", ""),
                summary=pkg.get("summary", "") or "",
                stars=pkg.get("stars", 0) or 0,
                dependent_count=pkg.get("dependent_count", 0) or 0,
                growth_pct=pkg.get("growth_pct", 0) or 0,
                version=pkg.get("version", "") or "",
                embedding_text=texts[j],
            )
            points.append(
                PointStruct(
                    id=next_id,
                    vector=embedding,
                    payload=payload.model_dump(),
                )
            )
            next_id += 1

        client.upsert(collection_name=QDRANT_COLLECTION, points=points)
        indexed += len(points)
        pbar.update(len(batch))
        pbar.set_postfix(ok=indexed, err=errors)

    pbar.close()
    return indexed, errors


if __name__ == "__main__":
    print("=" * 60)
    print("EMBED MISSING PACKAGES INTO QDRANT")
    print("=" * 60)

    print("\n[1/3] Scanning Qdrant for existing packages...")
    existing = get_qdrant_names()
    print(f"  Already in Qdrant: {len(existing):,}")

    print("\n[2/3] Finding packages in DuckDB missing from Qdrant...")
    missing = get_missing_packages(existing)
    print(f"  Missing: {len(missing):,}")

    if not missing:
        print("\nAll packages already in Qdrant!")
        sys.exit(0)

    print(f"\n[3/3] Embedding {len(missing):,} packages...")
    t0 = time.time()
    indexed, errors = embed_packages(missing)
    elapsed = time.time() - t0

    final_count = get_client().get_collection(QDRANT_COLLECTION).points_count
    print(f"\nDone! Embedded {indexed:,} packages in {elapsed / 60:.1f} min ({errors} errors)")
    print(f"Qdrant collection now has {final_count:,} vectors")
