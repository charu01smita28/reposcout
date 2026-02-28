"""
Add YoY growth trends to the packages table using dependents_2025.csv.

Computes growth_pct by comparing 2026 vs 2025 dependent counts.

Usage:
    python scripts/add_growth_data.py
"""

import duckdb
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "reposcout.db"
CSV_PATH = DATA_DIR / "layer2" / "dependents_2025.csv"

if not CSV_PATH.exists():
    print(f"[ERROR] {CSV_PATH} not found")
    exit(1)

db = duckdb.connect(str(DB_PATH))

# Load 2025 data as temp table
print("[...] Loading dependents_2025...")
db.sql(f"""
    CREATE TABLE dependents_2025 AS
    SELECT * FROM read_csv_auto('{CSV_PATH}', ignore_errors=true)
""")
count = db.sql("SELECT COUNT(*) FROM dependents_2025").fetchone()[0]
print(f"[OK] dependents_2025: {count:,} rows")

# Add growth columns to packages
print("[...] Computing growth trends...")
db.sql("""
    CREATE TABLE packages_with_growth AS
    SELECT
        p.*,
        old.dependent_count AS dependent_count_2025,
        ROUND((p.dependent_count - COALESCE(old.dependent_count, 0)) * 100.0
              / GREATEST(COALESCE(old.dependent_count, 1), 1), 1) AS growth_pct
    FROM packages p
    LEFT JOIN dependents_2025 old ON old.package_name = p.package_name
    ORDER BY p.dependent_count DESC
""")

# Replace old table
db.sql("DROP TABLE packages")
db.sql("ALTER TABLE packages_with_growth RENAME TO packages")
db.sql("DROP TABLE dependents_2025")

# Verify
print("\n" + "=" * 60)
print("GROWTH DATA ADDED")
print("=" * 60)

print(f"\n  Schema:")
print(db.sql("DESCRIBE packages").fetchdf().to_string(index=False))

print(f"\n  Top 10 fastest growing:")
print(db.sql("""
    SELECT package_name, dependent_count, dependent_count_2025, growth_pct
    FROM packages
    WHERE dependent_count_2025 > 10
    ORDER BY growth_pct DESC
    LIMIT 10
""").fetchdf().to_string(index=False))

print(f"\n  Top 10 by dependents (with growth):")
print(db.sql("""
    SELECT package_name, dependent_count, dependent_count_2025, growth_pct
    FROM packages
    LIMIT 10
""").fetchdf().to_string(index=False))

db.close()
print("\nDone! 'packages' table now has growth_pct and dependent_count_2025 columns.")
