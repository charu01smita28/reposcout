"""
Fetch monthly download stats from the pypistats.org API for top packages.

Uses the pypistats.org REST API (not the pypistats Python package) to get
monthly download counts (without mirrors) and stores them in a DuckDB table.

Usage:
    python scripts/fetch_download_stats.py              # top 500 packages
    python scripts/fetch_download_stats.py --limit 1000 # top N packages
    python scripts/fetch_download_stats.py --resume     # skip already fetched
"""

import argparse
import json
import time
import duckdb
import httpx
from tqdm import tqdm
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "reposcout.db"
CACHE_DIR = DATA_DIR / "download_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

PYPISTATS_URL = "https://pypistats.org/api/packages/{package_name}/overall"
RATE_LIMIT_SLEEP = 1.0
TIMEOUT = 15.0
MAX_RETRIES = 3


def get_package_names(limit: int, resume: bool) -> list[str]:
    """Get top packages by dependent_count, optionally skipping already fetched ones."""
    db = duckdb.connect(str(DB_PATH), read_only=True)

    query = "SELECT package_name FROM packages ORDER BY dependent_count DESC"
    if limit > 0:
        query += f" LIMIT {limit}"

    names = [row[0] for row in db.sql(query).fetchall()]

    if resume:
        already_fetched = set()
        try:
            rows = db.sql("SELECT DISTINCT package_name FROM download_stats").fetchall()
            already_fetched = {row[0] for row in rows}
        except duckdb.CatalogException:
            pass

        before = len(names)
        names = [n for n in names if n not in already_fetched]
        print(f"[INFO] Resuming: {before - len(names):,} already in DB, {len(names):,} remaining")

    db.close()
    return names


def fetch_one(client: httpx.Client, package_name: str) -> list[dict] | None:
    """Fetch monthly download stats for a single package. Returns list of {month, downloads} dicts."""
    cache_file = CACHE_DIR / f"{package_name.lower()}.json"

    # Check cache first
    if cache_file.exists():
        try:
            data = json.loads(cache_file.read_text())
            return parse_response(package_name, data)
        except (json.JSONDecodeError, OSError, KeyError):
            pass

    url = PYPISTATS_URL.format(package_name=package_name)
    params = {"period": "monthly", "mirrors": "false"}

    ...  # Retry loop with exponential backoff on 429/5xx removed for public repository
    return None


def parse_response(package_name: str, data: dict) -> list[dict]:
    """Extract without_mirrors entries from the pypistats API response."""
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


def fetch_all(package_names: list[str]) -> list[dict]:
    """Fetch download stats for all packages with proper rate limiting."""
    all_rows = []
    errors = 0

    with httpx.Client(timeout=TIMEOUT) as client:
        pbar = tqdm(package_names, desc="Fetching downloads", unit="pkg", ncols=80)

        for name in pbar:
            cache_file = CACHE_DIR / f"{name.lower()}.json"
            was_cached = cache_file.exists()

            result = fetch_one(client, name)

            if result is not None:
                all_rows.extend(result)
            else:
                errors += 1

            pbar.set_postfix(rows=len(all_rows), err=errors)

            # Only rate-limit when we actually hit the network
            if not was_cached:
                time.sleep(RATE_LIMIT_SLEEP)

        pbar.close()

    return all_rows


def load_into_duckdb(rows: list[dict]):
    """Insert download stats into DuckDB."""
    if not rows:
        print("[WARN] No rows to insert.")
        return

    db = duckdb.connect(str(DB_PATH))

    db.sql("""
        CREATE TABLE IF NOT EXISTS download_stats (
            package_name VARCHAR,
            month VARCHAR,
            downloads BIGINT
        )
    """)

    ...  # Dedup + insert logic removed for public repository

    db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch monthly download stats from pypistats.org")
    parser.add_argument("--limit", type=int, default=500, help="Top N packages by dependent_count (default: 500)")
    parser.add_argument("--resume", action="store_true", help="Skip packages already in download_stats table")
    args = parser.parse_args()

    print("=" * 60)
    print("DOWNLOAD STATS FETCHER (pypistats.org)")
    print("=" * 60)

    names = get_package_names(limit=args.limit, resume=args.resume)
    print(f"\n[...] Fetching download stats for {len(names):,} packages...")
    print(f"      Rate limit: {RATE_LIMIT_SLEEP}s per request")
    print(f"      Cache dir: {CACHE_DIR}")

    if not names:
        print("[INFO] Nothing to fetch. All packages already in DB.")
        exit(0)

    t0 = time.time()
    rows = fetch_all(names)
    elapsed = time.time() - t0

    print(f"\n[OK] Fetched {len(rows):,} data points in {elapsed/60:.1f} minutes")
    load_into_duckdb(rows)
    print("\nDone!")
