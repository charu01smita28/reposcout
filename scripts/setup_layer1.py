"""
Layer 1 — Historical Dependency Graph (Libraries.io 2020)

Run this AFTER setup_layer2.py. Adds historical tables to existing reposcout.db.

Usage:
    python scripts/setup_layer1.py                # projects + versions only (~5 min)
    python scripts/setup_layer1.py --with-deps    # + dependencies (~30-40 min)
"""

import argparse
import time
import duckdb
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "reposcout.db"
LAYER1_DIR = DATA_DIR / "layer1"


def find_csv(pattern: str) -> str | None:
    for path in LAYER1_DIR.rglob("*.csv"):
        if pattern in path.name.lower():
            return str(path)
    return None


db = duckdb.connect(str(DB_PATH))

print("=" * 60)
print("LAYER 1 — Historical Dependency Graph (Libraries.io 2020)")
print("=" * 60)

# ============ PROJECTS ============

projects_csv = find_csv("projects")
if not projects_csv:
    print(f"[ERROR] No projects CSV found in {LAYER1_DIR}")
    print("  Extract libraries.tar.gz into data/layer1/ first")
    exit(1)

print(f"\n[...] Loading lib_projects from {projects_csv}")
print("      Filtering to Platform='Pypi'...")
t0 = time.time()
db.sql(f"""
    CREATE TABLE lib_projects AS
    SELECT * FROM read_csv_auto('{projects_csv}', ignore_errors=true)
    WHERE Platform = 'Pypi'
""")
count = db.sql("SELECT COUNT(*) FROM lib_projects").fetchone()[0]
print(f"[OK] lib_projects: {count:,} rows in {time.time()-t0:.1f}s")

# ============ VERSIONS ============

versions_csv = find_csv("versions")
if versions_csv:
    print(f"\n[...] Loading lib_versions from {versions_csv}")
    print("      Filtering to Platform='Pypi'...")
    t0 = time.time()
    db.sql(f"""
        CREATE TABLE lib_versions AS
        SELECT * FROM read_csv_auto('{versions_csv}', ignore_errors=true)
        WHERE Platform = 'Pypi'
    """)
    count = db.sql("SELECT COUNT(*) FROM lib_versions").fetchone()[0]
    print(f"[OK] lib_versions: {count:,} rows in {time.time()-t0:.1f}s")
else:
    print("[WARN] Versions CSV not found — skipping")

# ============ DEPENDENCIES (optional) ============

parser = argparse.ArgumentParser()
parser.add_argument("--with-deps", action="store_true")
args = parser.parse_args()

if args.with_deps:
    deps_csv = find_csv("dependencies")
    if deps_csv:
        print(f"\n[...] Loading lib_deps from {deps_csv}")
        print("      Filtering to Platform='Pypi'... (this is the big one, be patient)")
        t0 = time.time()
        db.sql(f"""
            CREATE TABLE lib_deps AS
            SELECT * FROM read_csv_auto('{deps_csv}', ignore_errors=true)
            WHERE Platform = 'Pypi'
        """)
        count = db.sql("SELECT COUNT(*) FROM lib_deps").fetchone()[0]
        print(f"[OK] lib_deps: {count:,} rows in {time.time()-t0:.1f}s")

        print("[...] Creating indexes on lib_deps...")
        db.sql("CREATE INDEX IF NOT EXISTS idx_libdeps_proj ON lib_deps(Project_Name)")
        db.sql("CREATE INDEX IF NOT EXISTS idx_libdeps_dep ON lib_deps(Dependency_Name)")
        print("[OK] Indexes created")
    else:
        print("[WARN] Dependencies CSV not found")
else:
    print("\n[SKIP] lib_deps skipped (run with --with-deps to include)")

# ============ VERIFY ============

print("\n" + "=" * 60)
print("LAYER 1 LOADED")
print("=" * 60)

tables = db.sql("SHOW TABLES").fetchall()
for (name,) in tables:
    count = db.sql(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
    print(f"  {name}: {count:,} rows")

print(f"\n  Database: {DB_PATH}")
print(f"  Size: {DB_PATH.stat().st_size / (1024**2):.1f} MB")

print("\n  Sample from lib_projects:")
print(db.sql("SELECT Name, Stars, Dependents_Count FROM lib_projects ORDER BY Dependents_Count DESC LIMIT 10").fetchdf().to_string(index=False))

db.close()
print("\nDone! Layer 1 added to reposcout.db")
