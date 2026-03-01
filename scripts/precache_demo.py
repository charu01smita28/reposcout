"""
Pre-cache demo queries by hitting the live SSE endpoint.
Run with the backend already running on port 8000:

    python scripts/precache_demo.py          # all queries
    python scripts/precache_demo.py --new    # only new extras
"""

import httpx
import time
import sys

BASE = "http://localhost:8000"

# All unique (query, mode) pairs from suggestedQueries in sample-data.ts
QUERIES = [
    # auto mode
    ("How do Python projects handle rate limiting?", "auto"),
    ("Compare FastAPI vs Django vs Flask", "auto"),
    ("Which Python packages handle PDF parsing?", "auto"),
    ("Best Python libraries for web scraping", "auto"),
    # explore mode
    ("Best Python libraries for web scraping", "explore"),
    ("Best Python libraries for async processing", "explore"),
    ("Best Python libraries for file handling", "explore"),
    ("Best Python libraries for machine learning", "explore"),
    # compare mode
    ("Compare FastAPI vs Django vs Flask", "compare"),
    ("Compare requests vs httpx vs aiohttp", "compare"),
    ("Compare SQLAlchemy vs Django ORM vs Peewee", "compare"),
    ("Compare pytest vs unittest vs nose2", "compare"),
]

# Extra queries to cache (not in suggestion cards but good for demo)
EXTRA_QUERIES = [
    ("What are the fastest growing AI libraries in Python?", "auto"),
    ("Top trending Python libraries for building AI agents", "auto"),
]


def run_query(query: str, mode: str, index: int, total: int):
    print(f"\n[{index}/{total}] {mode}: {query}")
    print("  Streaming...", end="", flush=True)

    start = time.time()
    event_count = 0

    with httpx.Client(timeout=180.0) as client:
        with client.stream(
            "POST",
            f"{BASE}/api/search/stream",
            json={"query": query, "mode": mode},
        ) as resp:
            if resp.status_code != 200:
                print(f"  FAILED ({resp.status_code})")
                return False

            for line in resp.iter_lines():
                if line.startswith("data: "):
                    event_count += 1
                    if event_count % 20 == 0:
                        print(".", end="", flush=True)

    elapsed = time.time() - start
    print(f" done ({event_count} events, {elapsed:.1f}s)")
    return True


def main():
    # Check backend is running
    try:
        r = httpx.get(f"{BASE}/api/stats", timeout=5)
        r.raise_for_status()
    except Exception:
        print("ERROR: Backend not running on port 8000.")
        print("Start it first: uvicorn backend.main:app --reload --port 8000")
        sys.exit(1)

    if "--new" in sys.argv:
        queries = EXTRA_QUERIES
        print(f"Pre-caching {len(queries)} NEW queries only...")
    else:
        queries = QUERIES + EXTRA_QUERIES
        print(f"Pre-caching {len(queries)} demo queries...")

    print(f"Cache dir: data/stream_cache/\n")

    total = len(queries)
    failed = []
    for i, (query, mode) in enumerate(queries, 1):
        ok = run_query(query, mode, i, total)
        if not ok:
            failed.append((query, mode))

    print(f"\n{'='*50}")
    print(f"Done! {total - len(failed)}/{total} cached successfully.")
    if failed:
        print(f"Failed ({len(failed)}):")
        for q, m in failed:
            print(f"  - [{m}] {q}")


if __name__ == "__main__":
    main()
