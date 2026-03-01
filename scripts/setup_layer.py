"""
Setup — Fresh Ecosystem Snapshot (BigQuery/deps.dev)

Creates reposcout.db with fresh package data.

Usage:
    python scripts/setup_layer.py
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

# ============ JOINED VIEW ============
# Unified 'packages' table joining:
#   fresh_dependents (dep counts) + bridge (PyPI→GitHub) + github_projects (stars/forks/issues)
#   + optional YoY growth calculation from dependents_2025
# Uses ROW_NUMBER() to deduplicate multiple GitHub repos per package (picks highest stars)

...  # SQL join + growth calculation removed for public repository

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
