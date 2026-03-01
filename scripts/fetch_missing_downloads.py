"""
Fetch download stats for high-growth + AI packages missing from download_stats.

Usage:
    python scripts/fetch_missing_downloads.py
"""

import json
import time
import duckdb
import httpx
from pathlib import Path
from tqdm import tqdm

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "reposcout.db"
CACHE_DIR = DATA_DIR / "download_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

PYPISTATS_URL = "https://pypistats.org/api/packages/{}/overall"
RATE_LIMIT_SLEEP = 1.0
TIMEOUT = 15.0


def get_missing_packages() -> list[str]:
    """Find high-growth + AI packages not yet in download_stats.

    Tier 1: AI/ML packages with growth > 50% (matched by summary/keywords/name)
    Tier 2: Any package with growth > 200%
    Combined, deduplicated, minus already-fetched.
    """
    db = duckdb.connect(str(DB_PATH), read_only=True)

    existing = set(
        r[0] for r in db.sql("SELECT DISTINCT package_name FROM download_stats").fetchall()
    )
    print(f"Already in download_stats: {len(existing):,}")

    # Tier 1: AI/ML packages with growth > 50%
    tier1 = db.sql("""
        SELECT DISTINCT p.package_name, p.growth_pct, p.dependent_count
        FROM packages p
        JOIN pypi_metadata m ON LOWER(p.package_name) = LOWER(m.name)
        WHERE p.growth_pct > 50
        AND (
            LOWER(m.summary) LIKE '%machine learning%'
            OR LOWER(m.summary) LIKE '%deep learning%'
            OR LOWER(m.summary) LIKE '%language model%'
            OR LOWER(m.summary) LIKE '%llm%'
            OR LOWER(m.summary) LIKE '%transformer%'
            OR LOWER(m.summary) LIKE '%embedding%'
            OR LOWER(m.summary) LIKE '%vector%'
            OR LOWER(m.summary) LIKE '%agent%'
            ...  -- additional keyword filters removed for public repository
        )
        ORDER BY p.growth_pct DESC
        LIMIT 100
    """).fetchall()

    # Tier 2: top growth regardless of topic
    tier2 = db.sql("""
        SELECT package_name, growth_pct, dependent_count
        FROM packages
        WHERE growth_pct > 200
        ORDER BY growth_pct DESC
        LIMIT 150
    """).fetchall()

    ...  # Merge + dedup + filter logic removed for public repository

    db.close()
    return []


def parse_response(package_name: str, data: dict) -> list[dict]:
    entries = data.get("data", [])
    results = []
    for entry in entries:
        if entry.get("category") != "without_mirrors":
            continue
        month = entry.get("date")
        downloads = entry.get("downloads")
        if month and downloads is not None:
            results.append({
                "package_name": package_name,
                "month": month,
                "downloads": int(downloads),
            })
    return results


def fetch_all(names: list[str]) -> list[dict]:
    """Fetch with cache-first strategy + rate limiting."""
    all_rows = []
    errors = 0
    cached_hits = 0

    with httpx.Client(timeout=TIMEOUT) as client:
        pbar = tqdm(names, desc="Fetching", unit="pkg", ncols=90)

        for name in pbar:
            cache_file = CACHE_DIR / f"{name.lower()}.json"

            # Try cache first
            if cache_file.exists():
                try:
                    data = json.loads(cache_file.read_text())
                    result = parse_response(name, data)
                    if result:
                        all_rows.extend(result)
                    cached_hits += 1
                    pbar.set_postfix(rows=len(all_rows), err=errors, cached=cached_hits)
                    continue
                except (json.JSONDecodeError, OSError):
                    pass

            ...  # API fetch with retry + backoff removed for public repository

            pbar.set_postfix(rows=len(all_rows), err=errors, cached=cached_hits)
            time.sleep(RATE_LIMIT_SLEEP)

        pbar.close()

    return all_rows


def load_into_duckdb(rows: list[dict]):
    """Insert into DuckDB with dedup."""
    if not rows:
        print("[WARN] No rows to insert.")
        return

    db = duckdb.connect(str(DB_PATH))

    db.sql("""
        CREATE TABLE IF NOT EXISTS download_stats (
            package_name VARCHAR, month VARCHAR, downloads BIGINT
        )
    """)

    ...  # Dedup + batch insert logic removed for public repository

    db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("FETCH MISSING DOWNLOAD STATS (AI + high-growth packages)")
    print("=" * 60)

    names = get_missing_packages()

    if not names:
        print("\nAll packages already fetched!")
        exit(0)

    t0 = time.time()
    rows = fetch_all(names)
    elapsed = time.time() - t0

    print(f"\nFetched {len(rows):,} data points in {elapsed:.0f}s")
    load_into_duckdb(rows)
    print("Done!")
