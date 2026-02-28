"""
Load BigQuery-exported CSV data into DuckDB as supplementary fresh data.

Usage:
    python -m scripts.load_bigquery --csv path/to/bigquery_export.csv

Place your BigQuery CSV exports in data/ before running.
Expected CSV files:
  - bigquery_packages.csv (from deps.dev PackageVersions query)
  - bigquery_downloads.csv (from PyPI downloads query, optional)
"""

import argparse
import time
import duckdb
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "reposcout.db"


def load_bigquery_packages(csv_path: str):
    conn = duckdb.connect(str(DB_PATH))

    print(f"[...] Loading BigQuery packages from {csv_path}")
    t0 = time.time()

    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS projects_fresh AS
        SELECT * FROM read_csv_auto('{csv_path}', ignore_errors=true)
    """)

    count = conn.execute("SELECT COUNT(*) FROM projects_fresh").fetchone()[0]
    print(f"[OK] Loaded {count:,} fresh packages in {time.time()-t0:.1f}s")

    # Create a unified view that prefers fresh data
    conn.execute("DROP VIEW IF EXISTS packages_unified")
    conn.execute("""
        CREATE VIEW packages_unified AS
        SELECT
            COALESCE(f.Name, p.Name) AS name,
            COALESCE(f.Description, p.Description) AS description,
            COALESCE(f.Stars, p.Stars) AS stars,
            COALESCE(f.Forks, p.Forks) AS forks,
            p.Dependents_Count AS dependents_count,
            COALESCE(f.Repository_URL, p.Repository_URL) AS repository_url,
            COALESCE(f.Homepage_URL, p.Homepage_URL) AS homepage_url,
            p.Licenses AS licenses,
            CASE WHEN f.Name IS NOT NULL THEN 'fresh' ELSE 'historical' END AS data_source
        FROM projects p
        FULL OUTER JOIN projects_fresh f
            ON LOWER(p.Name) = LOWER(f.Name)
    """)

    print("[OK] Created packages_unified view (fresh data preferred)")

    # Summary
    unified_count = conn.execute("SELECT COUNT(*) FROM packages_unified").fetchone()[0]
    fresh_only = conn.execute("SELECT COUNT(*) FROM packages_unified WHERE data_source = 'fresh'").fetchone()[0]
    print(f"  Unified packages: {unified_count:,}")
    print(f"  Fresh-only (not in Libraries.io): {fresh_only:,}")

    conn.close()


def load_bigquery_downloads(csv_path: str):
    conn = duckdb.connect(str(DB_PATH))

    print(f"[...] Loading BigQuery download stats from {csv_path}")
    t0 = time.time()

    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS download_stats AS
        SELECT * FROM read_csv_auto('{csv_path}', ignore_errors=true)
    """)

    count = conn.execute("SELECT COUNT(*) FROM download_stats").fetchone()[0]
    print(f"[OK] Loaded download stats for {count:,} packages in {time.time()-t0:.1f}s")

    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load BigQuery CSV exports into DuckDB")
    parser.add_argument("--packages", type=str, help="Path to BigQuery packages CSV")
    parser.add_argument("--downloads", type=str, help="Path to BigQuery downloads CSV")
    args = parser.parse_args()

    if args.packages:
        load_bigquery_packages(args.packages)
    if args.downloads:
        load_bigquery_downloads(args.downloads)
    if not args.packages and not args.downloads:
        # Auto-detect CSVs in data dir
        pkg_csv = DATA_DIR / "bigquery_packages.csv"
        dl_csv = DATA_DIR / "bigquery_downloads.csv"
        if pkg_csv.exists():
            load_bigquery_packages(str(pkg_csv))
        else:
            print(f"[INFO] No BigQuery packages CSV found at {pkg_csv}")
        if dl_csv.exists():
            load_bigquery_downloads(str(dl_csv))
