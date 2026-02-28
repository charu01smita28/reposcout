"""
View Qdrant collection contents.

Usage:
    python scripts/view_qdrant.py                    # show collection stats + first 10 points
    python scripts/view_qdrant.py --search "web framework"  # search (needs MISTRAL_API_KEY)
    python scripts/view_qdrant.py --all              # show all points
"""

import argparse
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from backend.config import QDRANT_COLLECTION
from backend.utils.qdrant_client import get_client


def main():
    parser = argparse.ArgumentParser(description="View Qdrant collection")
    parser.add_argument("--search", type=str, default="", help="Semantic search query")
    parser.add_argument("--limit", type=int, default=10, help="Number of results")
    parser.add_argument("--all", action="store_true", help="Show all points")
    args = parser.parse_args()

    client = get_client()

    # Collection stats
    info = client.get_collection(QDRANT_COLLECTION)
    print("=" * 70)
    print(f"QDRANT COLLECTION: {QDRANT_COLLECTION}")
    print("=" * 70)
    print(f"  Points:       {info.points_count:,}")
    print(f"  Vector dim:   {info.config.params.vectors.size}")
    print(f"  Distance:     {info.config.params.vectors.distance}")
    print(f"  Status:       {info.status}")
    print()

    if args.search:
        # Semantic search
        from backend.utils.qdrant_client import get_embedding
        print(f"Searching: \"{args.search}\"")
        print("-" * 70)

        query_vector = get_embedding(args.search)
        results = client.search(
            collection_name=QDRANT_COLLECTION,
            query_vector=query_vector,
            limit=args.limit,
        )

        for i, hit in enumerate(results):
            p = hit.payload
            print(f"\n  [{i+1}] score={hit.score:.4f}  {p['name']}")
            print(f"      summary:    {p.get('summary', '')[:80]}")
            print(f"      stars:      {p.get('stars', 0):,}")
            print(f"      dependents: {p.get('dependent_count', 0):,}")
            print(f"      growth:     {p.get('growth_pct', 0)}%")
            print(f"      version:    {p.get('version', '')}")
    else:
        # Browse points
        limit = info.points_count if args.all else args.limit
        print(f"Showing {limit} points:")
        print("-" * 70)

        points, _ = client.scroll(
            collection_name=QDRANT_COLLECTION,
            limit=limit,
            with_vectors=False,
        )

        for p in points:
            payload = p.payload
            name = payload.get("name", "?")
            summary = payload.get("summary", "")[:60]
            stars = payload.get("stars", 0)
            deps = payload.get("dependent_count", 0)
            growth = payload.get("growth_pct", 0)
            version = payload.get("version", "")

            print(f"  [{p.id:>5}] {name:25s}  stars={stars:>7,}  deps={deps:>7,}  growth={growth:>6}%  v{version}")
            if summary:
                print(f"          {summary}")

    client.close()


if __name__ == "__main__":
    main()
