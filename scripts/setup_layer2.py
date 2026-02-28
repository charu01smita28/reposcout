"""
Layer 2 — Fresh Ecosystem Snapshot (BigQuery/deps.dev)

Run this first. Creates a standalone reposcout.db with fresh data.

Usage:
    python scripts/setup_layer2.py
"""

import duckdb
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "reposcout.db"

db = duckdb.connect(str(DB_PATH))

# ============ LAYER 2 (Fresh - BigQuery) ============

# Load fresh dependent counts
print("[...] Loading fresh_dependents...")
db.sql(f"""
    CREATE TABLE fresh_dependents AS
    SELECT * FROM read_csv_auto('{DATA_DIR}/layer2/dependents.csv', ignore_errors=true)
""")
count = db.sql("SELECT COUNT(*) FROM fresh_dependents").fetchone()[0]
print(f"[OK] fresh_dependents: {count:,} rows")

# Load bridge (PyPI name → GitHub repo)
print("[...] Loading bridge...")
db.sql(f"""
    CREATE TABLE bridge AS
    SELECT * FROM read_csv_auto('{DATA_DIR}/layer2/bridge.csv', ignore_errors=true)
""")
count = db.sql("SELECT COUNT(*) FROM bridge").fetchone()[0]
print(f"[OK] bridge: {count:,} rows")

# Load GitHub project metadata
print("[...] Loading github_projects...")
db.sql(f"""
    CREATE TABLE github_projects AS
    SELECT * FROM read_csv_auto('{DATA_DIR}/layer2/projects.csv', ignore_errors=true)
""")
count = db.sql("SELECT COUNT(*) FROM github_projects").fetchone()[0]
print(f"[OK] github_projects: {count:,} rows")

# Load 2025 dependents for growth trends (optional)
dependents_2025_path = DATA_DIR / "layer2" / "dependents_2025.csv"
has_2025 = dependents_2025_path.exists()
if has_2025:
    print("[...] Loading dependents_2025 for growth trends...")
    db.sql(f"""
        CREATE TABLE dependents_2025 AS
        SELECT * FROM read_csv_auto('{dependents_2025_path}', ignore_errors=true)
    """)
    count = db.sql("SELECT COUNT(*) FROM dependents_2025").fetchone()[0]
    print(f"[OK] dependents_2025: {count:,} rows")
else:
    print("[INFO] No dependents_2025.csv found — growth trends will be skipped")

# ============ JOINED VIEW ============

growth_cols = ""
growth_join = ""
if has_2025:
    growth_cols = """,
        old.dependent_count AS dependent_count_2025,
        ROUND((d.dependent_count - COALESCE(old.dependent_count, 0)) * 100.0
              / GREATEST(COALESCE(old.dependent_count, 1), 1), 1) AS growth_pct"""
    growth_join = "LEFT JOIN dependents_2025 old ON old.package_name = d.package_name"

print("[...] Creating unified 'packages' table...")
db.sql(f"""
    CREATE TABLE packages AS
    WITH bridge_dedup AS (
        SELECT DISTINCT package_name, github_repo
        FROM bridge
    ),
    ranked AS (
        SELECT
            d.package_name,
            d.dependent_count,
            b.github_repo,
            g.StarsCount AS stars,
            g.ForksCount AS forks,
            g.OpenIssuesCount AS open_issues,
            g.Description AS description,
            g.Homepage AS homepage
            {growth_cols},
            ROW_NUMBER() OVER (
                PARTITION BY d.package_name
                ORDER BY g.StarsCount DESC NULLS LAST
            ) AS rn
        FROM fresh_dependents d
        LEFT JOIN bridge_dedup b ON b.package_name = d.package_name
        LEFT JOIN github_projects g ON g.Name = b.github_repo
        {growth_join}
    )
    SELECT *  EXCLUDE (rn)
    FROM ranked
    WHERE rn = 1
    ORDER BY dependent_count DESC
""")
# ============ DROP INTERMEDIATE TABLES ============

print("[...] Dropping intermediate tables (only 'packages' matters)...")
db.sql("DROP TABLE fresh_dependents")
db.sql("DROP TABLE bridge")
db.sql("DROP TABLE github_projects")
if has_2025:
    db.sql("DROP TABLE dependents_2025")
print("[OK] Dropped intermediate tables")

# ============ VERIFY ============

count = db.sql("SELECT COUNT(*) FROM packages").fetchone()[0]
print("\n" + "=" * 60)
print(f"LAYER 2 READY — 'packages' table: {count:,} rows")
print("=" * 60)

print(f"\n  Schema:")
print(db.sql("DESCRIBE packages").fetchdf().to_string(index=False))

print(f"\n  Database: {DB_PATH}")
print(f"  Size: {DB_PATH.stat().st_size / (1024**2):.1f} MB")

print(f"\n  Top 10 packages:")
print(db.sql("SELECT package_name, dependent_count, stars, forks FROM packages LIMIT 10").fetchdf().to_string(index=False))

db.close()
print("\nDone! Only 'packages' table remains. Clean.")
