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
RATE_LIMIT_SLEEP = 1.0  # 1 request per second
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
        # Check which packages already exist in download_stats table
        already_fetched = set()
        try:
            rows = db.sql("SELECT DISTINCT package_name FROM download_stats").fetchall()
            already_fetched = {row[0] for row in rows}
        except duckdb.CatalogException:
            # Table doesn't exist yet — nothing to skip
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

    for attempt in range(MAX_RETRIES):
        try:
            response = client.get(url, params=params)

            if response.status_code == 404:
                # Package not found on pypistats — skip silently
                return None

            if response.status_code == 429:
                # Rate limited — back off and retry
                wait = 2 ** (attempt + 1)
                time.sleep(wait)
                continue

            if response.status_code >= 500:
                # Server error — back off and retry
                wait = 2 ** attempt
                time.sleep(wait)
                continue

            if response.status_code != 200:
                return None

            data = response.json()

            # Cache raw JSON response to disk
            cache_file.write_text(json.dumps(data))

            return parse_response(package_name, data)

        except (httpx.RequestError, httpx.TimeoutException):
            wait = 2 ** attempt
            time.sleep(wait)
            continue
        except (json.JSONDecodeError, KeyError):
            return None

    return None  # all retries exhausted


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

    # Create table if it doesn't exist
    db.sql("""
        CREATE TABLE IF NOT EXISTS download_stats (
            package_name VARCHAR,
            month VARCHAR,
            downloads BIGINT
        )
    """)

    # Deduplicate: remove any existing rows for packages we're about to insert
    package_names = list({r["package_name"] for r in rows})
    # Delete in batches to avoid overly long IN clauses
    batch_size = 500
    for i in range(0, len(package_names), batch_size):
        batch = package_names[i:i + batch_size]
        placeholders = ", ".join(f"'{name}'" for name in batch)
        db.sql(f"DELETE FROM download_stats WHERE package_name IN ({placeholders})")

    # Insert new data via temp JSON file
    temp_file = DATA_DIR / "download_stats_temp.json"
    temp_file.write_text(json.dumps(rows))

    db.sql(f"""
        INSERT INTO download_stats
        SELECT package_name, month, downloads
        FROM read_json_auto('{temp_file}')
    """)

    temp_file.unlink()

    # Create index
    try:
        db.sql("CREATE INDEX idx_dl_package ON download_stats(package_name)")
    except duckdb.CatalogException:
        pass  # index already exists

    # Verify
    total_rows = db.sql("SELECT COUNT(*) FROM download_stats").fetchone()[0]
    total_pkgs = db.sql("SELECT COUNT(DISTINCT package_name) FROM download_stats").fetchone()[0]
    print(f"\n[OK] download_stats: {total_rows:,} rows across {total_pkgs:,} packages")

    print(f"\n  Schema:")
    print(db.sql("DESCRIBE download_stats").fetchdf().to_string(index=False))

    print(f"\n  Sample (top packages, latest month):")
    print(db.sql("""
        SELECT package_name, month, downloads
        FROM download_stats
        WHERE month = (SELECT MAX(month) FROM download_stats)
        ORDER BY downloads DESC
        LIMIT 10
    """).fetchdf().to_string(index=False))

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

    print(f"\n  Cache dir: {CACHE_DIR} ({sum(1 for _ in CACHE_DIR.glob('*.json')):,} files)")
    print(f"  Database: {DB_PATH}")
    print(f"  Size: {DB_PATH.stat().st_size / (1024**2):.1f} MB")
    print("\nDone!")
