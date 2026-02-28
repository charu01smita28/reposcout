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

sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "scripts"))

from backend.config import QDRANT_COLLECTION, EMBEDDING_DIM
from backend.models import QdrantPayload
from backend.utils.qdrant_client import get_client, get_embeddings_batch, ensure_collection
from text_cleaner import build_embedding_text

BATCH_SIZE = 50  # Mistral embed API batch size


def load_packages() -> list[dict]:
    """Load packages with rich metadata from DuckDB.
    Joins packages (Layer 2 stats) with pypi_metadata (rich descriptions).
    Orders by dependent_count DESC for priority embedding."""
    ...  # DuckDB query removed for public repository
    return []


def generate_and_index(packages: list[dict], resume: bool = False):
    """Embed packages in batches via Mistral Embed API and upsert into Qdrant.

    Features:
    - Resume support: skips already-indexed packages
    - Rate limit handling: auto-retry with 30s backoff on 429
    - Rich payload: name, summary, stars, deps, growth, version, embedding_text
    - Progress bar via tqdm
    """
    ensure_collection()
    client = get_client()

    ...  # Embedding loop removed for public repository


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

    client = get_client()
    client.close()

    print(f"\nDone! Qdrant collection: '{QDRANT_COLLECTION}'")
    print(f"Embedding dim: {EMBEDDING_DIM}")
