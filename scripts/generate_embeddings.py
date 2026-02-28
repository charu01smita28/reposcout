"""
Generate embeddings for Python package descriptions and index into Qdrant.

Usage:
    python -m scripts.generate_embeddings

This reads package descriptions from DuckDB, embeds them with Mistral embed,
and stores them in Qdrant for semantic search.
"""

import time
import duckdb
from pathlib import Path
from qdrant_client.models import PointStruct

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "reposcout.db"

# Add parent to path so we can import backend modules
import sys
sys.path.insert(0, str(BASE_DIR))

from backend.config import QDRANT_PATH, QDRANT_COLLECTION, EMBEDDING_DIM
from backend.utils.qdrant_client import get_client, get_embeddings_batch, ensure_collection

BATCH_SIZE = 50  # Mistral embed API batch size


def load_descriptions() -> list[dict]:
    conn = duckdb.connect(str(DB_PATH), read_only=True)

    print("[...] Loading package descriptions from DuckDB...")
    df = conn.execute("""
        SELECT
            Name,
            Description,
            Stars,
            Dependents_Count,
            Repository_URL
        FROM projects
        WHERE Description IS NOT NULL
          AND LENGTH(TRIM(Description)) > 10
        ORDER BY Dependents_Count DESC
    """).fetchdf()

    conn.close()
    print(f"[OK] Loaded {len(df):,} packages with descriptions")
    return df.to_dict(orient="records")


def generate_and_index(packages: list[dict], start_from: int = 0):
    ensure_collection()
    client = get_client()

    total = len(packages)
    print(f"\n[...] Generating embeddings for {total:,} packages")
    print(f"      Batch size: {BATCH_SIZE}")
    print(f"      Estimated batches: {total // BATCH_SIZE + 1}")

    if start_from > 0:
        print(f"      Resuming from index {start_from}")

    t0 = time.time()
    indexed = 0
    errors = 0

    for i in range(start_from, total, BATCH_SIZE):
        batch = packages[i : i + BATCH_SIZE]
        texts = [
            f"{pkg.get('Name', '')}: {pkg.get('Description', '')}"
            for pkg in batch
        ]

        try:
            embeddings = get_embeddings_batch(texts)
        except Exception as e:
            errors += 1
            print(f"  [ERROR] Batch {i//BATCH_SIZE}: {e}")
            if "rate" in str(e).lower():
                print("  [WAIT] Rate limited, sleeping 10s...")
                time.sleep(10)
                try:
                    embeddings = get_embeddings_batch(texts)
                except Exception:
                    continue
            else:
                continue

        points = []
        for j, (pkg, embedding) in enumerate(zip(batch, embeddings)):
            points.append(
                PointStruct(
                    id=i + j,
                    vector=embedding,
                    payload={
                        "name": pkg.get("Name", ""),
                        "description": pkg.get("Description", ""),
                        "stars": pkg.get("Stars", 0) or 0,
                        "dependents_count": pkg.get("Dependents_Count", 0) or 0,
                        "repository_url": pkg.get("Repository_URL", ""),
                    },
                )
            )

        client.upsert(collection_name=QDRANT_COLLECTION, points=points)
        indexed += len(points)

        elapsed = time.time() - t0
        rate = indexed / elapsed if elapsed > 0 else 0
        eta = (total - i - BATCH_SIZE) / rate if rate > 0 else 0

        if (i // BATCH_SIZE) % 20 == 0:
            print(
                f"  [{indexed:,}/{total:,}] "
                f"{indexed/total*100:.1f}% | "
                f"{rate:.0f} pkg/s | "
                f"ETA: {eta/60:.1f}min | "
                f"Errors: {errors}"
            )

    elapsed = time.time() - t0
    print(f"\n[OK] Indexed {indexed:,} packages in {elapsed/60:.1f} minutes")
    print(f"     Errors: {errors}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="Limit number of packages (0=all)")
    parser.add_argument("--resume", type=int, default=0, help="Resume from index N")
    args = parser.parse_args()

    packages = load_descriptions()
    if args.limit > 0:
        packages = packages[:args.limit]
        print(f"[INFO] Limited to top {args.limit} packages")

    generate_and_index(packages, start_from=args.resume)
