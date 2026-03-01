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
    """Find high-growth + AI packages not yet in download_stats."""
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
            OR LOWER(m.summary) LIKE '%artificial intelligence%'
            OR LOWER(m.summary) LIKE '%neural%'
            OR LOWER(m.summary) LIKE '%nlp%'
            OR LOWER(m.summary) LIKE '%language model%'
            OR LOWER(m.summary) LIKE '%llm%'
            OR LOWER(m.summary) LIKE '%transformer%'
            OR LOWER(m.summary) LIKE '%embedding%'
            OR LOWER(m.summary) LIKE '%vector%'
            OR LOWER(m.summary) LIKE '%agent%'
            OR LOWER(m.summary) LIKE '%generative%'
            OR LOWER(m.summary) LIKE '%chatbot%'
            OR LOWER(m.summary) LIKE '%computer vision%'
            OR LOWER(m.summary) LIKE '%reinforcement%'
            OR LOWER(m.summary) LIKE '%model serving%'
            OR LOWER(m.summary) LIKE '%mlops%'
            OR LOWER(m.keywords) LIKE '%machine-learning%'
            OR LOWER(m.keywords) LIKE '%deep-learning%'
            OR LOWER(m.keywords) LIKE '%ai%'
            OR LOWER(m.keywords) LIKE '%llm%'
            OR LOWER(p.package_name) LIKE '%langchain%'
            OR LOWER(p.package_name) LIKE '%openai%'
            OR LOWER(p.package_name) LIKE '%llm%'
            OR LOWER(p.package_name) LIKE '%agent%'
            OR LOWER(p.package_name) LIKE '%mcp%'
            OR LOWER(p.package_name) LIKE '%anthropic%'
            OR LOWER(p.package_name) LIKE '%mistral%'
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

    combined = {}
    for name, growth, deps in tier1:
        combined[name] = (growth, deps)
    for name, growth, deps in tier2:
        if name not in combined:
            combined[name] = (growth, deps)

    # Filter out already fetched
    missing = {k: v for k, v in combined.items() if k not in existing}

    db.close()

    print(f"Tier 1 (AI + growth>50%): {len(tier1)}")
    print(f"Tier 2 (growth>200%):     {len(tier2)}")
    print(f"Combined unique:          {len(combined)}")
    print(f"After removing existing:  {len(missing)}")

    # Sort by growth desc for nice progress output
    return sorted(missing.keys(), key=lambda n: missing[n][0] or 0, reverse=True)


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

            # Fetch from API
            for attempt in range(3):
                try:
                    resp = client.get(
                        PYPISTATS_URL.format(name),
                        params={"period": "monthly", "mirrors": "false"},
                    )

                    if resp.status_code == 404:
                        errors += 1
                        break
                    elif resp.status_code == 429:
                        wait = 2 ** (attempt + 1)
                        tqdm.write(f"  Rate limited on {name}, waiting {wait}s...")
                        time.sleep(wait)
                        continue
                    elif resp.status_code == 200:
                        data = resp.json()
                        cache_file.write_text(json.dumps(data))
                        result = parse_response(name, data)
                        if result:
                            all_rows.extend(result)
                        break
                    else:
                        errors += 1
                        break
                except (httpx.RequestError, httpx.TimeoutException):
                    time.sleep(2 ** attempt)
                    continue

            pbar.set_postfix(rows=len(all_rows), err=errors, cached=cached_hits)
            time.sleep(RATE_LIMIT_SLEEP)

        pbar.close()

    return all_rows


def load_into_duckdb(rows: list[dict]):
    if not rows:
        print("[WARN] No rows to insert.")
        return

    db = duckdb.connect(str(DB_PATH))

    db.sql("""
        CREATE TABLE IF NOT EXISTS download_stats (
            package_name VARCHAR, month VARCHAR, downloads BIGINT
        )
    """)

    # Deduplicate
    pkg_names = list({r["package_name"] for r in rows})
    for i in range(0, len(pkg_names), 500):
        batch = pkg_names[i : i + 500]
        placeholders = ", ".join(f"'{n}'" for n in batch)
        db.sql(f"DELETE FROM download_stats WHERE package_name IN ({placeholders})")

    # Insert via temp file
    temp_file = DATA_DIR / "dl_temp.json"
    temp_file.write_text(json.dumps(rows))
    db.sql(f"""
        INSERT INTO download_stats
        SELECT package_name, month, downloads
        FROM read_json_auto('{temp_file}')
    """)
    temp_file.unlink()

    total_rows = db.sql("SELECT COUNT(*) FROM download_stats").fetchone()[0]
    total_pkgs = db.sql("SELECT COUNT(DISTINCT package_name) FROM download_stats").fetchone()[0]
    print(f"\n[OK] download_stats: {total_rows:,} rows across {total_pkgs:,} packages")

    db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("FETCH MISSING DOWNLOAD STATS (AI + high-growth packages)")
    print("=" * 60)

    names = get_missing_packages()

    if not names:
        print("\nAll packages already fetched!")
        exit(0)

    cached = sum(1 for n in names if (CACHE_DIR / f"{n.lower()}.json").exists())
    net_fetch = len(names) - cached
    print(f"\nPackages to process: {len(names)} ({cached} cached, {net_fetch} from API)")
    print(f"Estimated time: ~{net_fetch / 60:.1f} minutes")
    print()

    t0 = time.time()
    rows = fetch_all(names)
    elapsed = time.time() - t0

    print(f"\nFetched {len(rows):,} data points in {elapsed:.0f}s")

    load_into_duckdb(rows)
    print("Done!")
