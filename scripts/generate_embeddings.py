"""
Generate embeddings for Python package descriptions and index into Qdrant.

Combines data from packages + pypi_metadata tables to create rich embedding text:
  - Package name + summary
  - Full README description (truncated to 8K chars for embedding)
  - Keywords and classifiers

Uses Mistral Embed API for embeddings, stores in local Qdrant.

Usage:
    python scripts/generate_embeddings.py               # all packages
    python scripts/generate_embeddings.py --limit 1000   # top N only
    python scripts/generate_embeddings.py --resume       # skip already indexed
"""

import argparse
import sys
import time
import duckdb
from pathlib import Path
from tqdm import tqdm
from qdrant_client.models import PointStruct

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "reposcout.db"

# Add parent + scripts to path
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "scripts"))

from backend.config import QDRANT_COLLECTION, EMBEDDING_DIM
from backend.models import QdrantPayload
from backend.utils.qdrant_client import get_client, get_embeddings_batch, ensure_collection
from text_cleaner import build_embedding_text

BATCH_SIZE = 50  # Mistral embed API batch size


def load_packages() -> list[dict]:
    """Load packages with rich metadata from DuckDB."""
    conn = duckdb.connect(str(DB_PATH), read_only=True)

    print("[...] Loading packages with rich metadata from DuckDB...")

    # Join packages (Layer 2 stats) with pypi_metadata (rich descriptions)
    df = conn.execute("""
        SELECT
            p.package_name,
            p.dependent_count,
            p.stars,
            p.github_repo,
            p.growth_pct,
            COALESCE(m.summary, '') AS summary,
            COALESCE(m.description, '') AS description,
            COALESCE(m.keywords, '') AS keywords,
            COALESCE(m.classifiers, '[]') AS classifiers,
            COALESCE(m.version, '') AS version,
            COALESCE(m.total_versions, 0) AS total_versions,
            m.latest_release_date
        FROM packages p
        LEFT JOIN pypi_metadata m ON LOWER(p.package_name) = LOWER(m.name)
        WHERE COALESCE(m.summary, '') != '' OR COALESCE(m.description, '') != ''
        ORDER BY p.dependent_count DESC
    """).fetchdf()

    conn.close()
    print(f"[OK] Loaded {len(df):,} packages with metadata")
    return df.to_dict(orient="records")



def generate_and_index(packages: list[dict], resume: bool = False):
    ensure_collection()
    client = get_client()

    # If resuming, check how many are already indexed
    start_from = 0
    if resume:
        try:
            collection_info = client.get_collection(QDRANT_COLLECTION)
            existing = collection_info.points_count
            if existing > 0:
                start_from = existing
                print(f"[INFO] Resuming: {existing:,} already indexed, starting from index {start_from}")
        except Exception:
            pass

    total = len(packages)
    remaining = total - start_from
    if remaining <= 0:
        print(f"[OK] All {total:,} packages already indexed!")
        return

    print(f"\n[...] Generating embeddings for {remaining:,} packages (of {total:,} total)")
    print(f"      Batch size: {BATCH_SIZE}")
    print(f"      Estimated API calls: {remaining // BATCH_SIZE + 1}")

    t0 = time.time()
    indexed = 0
    errors = 0

    pbar = tqdm(total=remaining, desc="Embedding", unit="pkg", ncols=90)

    for i in range(start_from, total, BATCH_SIZE):
        batch = packages[i : i + BATCH_SIZE]

        # Build rich text for each package
        texts = [build_embedding_text(pkg) for pkg in batch]

        # Get embeddings from Mistral
        try:
            embeddings = get_embeddings_batch(texts)
        except Exception as e:
            errors += 1
            error_str = str(e).lower()
            if "rate" in error_str or "429" in error_str:
                pbar.write(f"  [WAIT] Rate limited, sleeping 30s...")
                time.sleep(30)
                try:
                    embeddings = get_embeddings_batch(texts)
                except Exception:
                    pbar.write(f"  [ERROR] Retry failed at batch {i // BATCH_SIZE}")
                    pbar.update(len(batch))
                    continue
            else:
                pbar.write(f"  [ERROR] Batch {i // BATCH_SIZE}: {e}")
                pbar.update(len(batch))
                continue

        # Build Qdrant points with payload
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
                    id=i + j,
                    vector=embedding,
                    payload=payload.model_dump(),
                )
            )

        client.upsert(collection_name=QDRANT_COLLECTION, points=points)
        indexed += len(points)
        pbar.update(len(batch))
        pbar.set_postfix(ok=indexed, err=errors)

    pbar.close()

    elapsed = time.time() - t0
    print(f"\n[OK] Indexed {indexed:,} packages in {elapsed / 60:.1f} minutes")
    print(f"     Errors: {errors}")
    print(f"     Total in collection: {indexed + start_from:,}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Mistral embeddings and index into Qdrant")
    parser.add_argument("--limit", type=int, default=0, help="Only embed top N packages (0=all)")
    parser.add_argument("--resume", action="store_true", help="Skip already indexed packages")
    args = parser.parse_args()

    packages = load_packages()
    if args.limit > 0:
        packages = packages[:args.limit]
        print(f"[INFO] Limited to top {args.limit} packages")

    generate_and_index(packages, resume=args.resume)

    # Explicitly close Qdrant before exit to avoid shutdown error
    client = get_client()
    client.close()

    print(f"\nDone! Qdrant collection: '{QDRANT_COLLECTION}'")
    print(f"Embedding dim: {EMBEDDING_DIM}")
