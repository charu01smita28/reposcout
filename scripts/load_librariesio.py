"""
Load Libraries.io CSV data into DuckDB, filtered to PyPI packages only.

Usage:
    python -m scripts.load_librariesio                # Load projects + versions (fast, ~5 min)
    python -m scripts.load_librariesio --with-deps    # Load everything including deps (~30-40 min)

Expects the extracted CSVs in a directory. Will auto-extract from tar.gz if needed.
"""

import argparse
import os
import sys
import tarfile
import time
import duckdb
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "reposcout.db"

# Path to the downloaded tar.gz
TAR_PATH = Path("/Users/charusmitadhiman/Downloads/libraries.tar.gz")
EXTRACT_DIR = DATA_DIR / "librariesio_raw"


def extract_tar():
    if EXTRACT_DIR.exists() and any(EXTRACT_DIR.rglob("*.csv")):
        print(f"[OK] CSV files already extracted in {EXTRACT_DIR}")
        return

    if not TAR_PATH.exists():
        print(f"[ERROR] Tar file not found at {TAR_PATH}")
        print("Update TAR_PATH in this script to point to your libraries.tar.gz")
        sys.exit(1)

    print(f"[...] Extracting {TAR_PATH} to {EXTRACT_DIR}")
    print("      This may take a while for 25GB...")
    EXTRACT_DIR.mkdir(parents=True, exist_ok=True)

    with tarfile.open(TAR_PATH, "r:gz") as tar:
        tar.extractall(path=EXTRACT_DIR)

    print(f"[OK] Extraction complete")


def find_csv(pattern: str) -> str | None:
    for path in EXTRACT_DIR.rglob("*.csv"):
        if pattern in path.name.lower():
            return str(path)
    return None


def load_data(with_deps: bool = False):
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Remove existing DB to start fresh
    if DB_PATH.exists():
        DB_PATH.unlink()
        print(f"[OK] Removed existing database")

    conn = duckdb.connect(str(DB_PATH))

    # Find the CSV files
    projects_csv = find_csv("projects")
    deps_csv = find_csv("dependencies") if with_deps else None
    versions_csv = find_csv("versions")

    if not projects_csv:
        print("[ERROR] Could not find projects CSV file")
        print(f"  Searched in: {EXTRACT_DIR}")
        print(f"  Files found: {list(EXTRACT_DIR.rglob('*.csv'))[:10]}")
        sys.exit(1)

    # --- Load Projects (filtered to PyPI) ---
    print(f"\n[...] Loading projects from {projects_csv}")
    print("      Filtering to Platform='Pypi'...")
    t0 = time.time()

    conn.execute(f"""
        CREATE TABLE projects AS
        SELECT * FROM read_csv_auto('{projects_csv}', ignore_errors=true)
        WHERE Platform = 'Pypi'
    """)

    count = conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
    print(f"[OK] Loaded {count:,} PyPI projects in {time.time()-t0:.1f}s")

    # Create indexes for fast lookups
    print("[...] Creating indexes on projects...")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_projects_name ON projects(Name)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_projects_name_lower ON projects(LOWER(Name))")
    print("[OK] Projects indexes created")

    # --- Load Dependencies (filtered to PyPI) --- OPTIONAL, pass --with-deps
    if deps_csv:
        print(f"\n[...] Loading dependencies from {deps_csv}")
        print("      Filtering to Platform='Pypi'... (this is the big one, ~235M rows)")
        t0 = time.time()

        conn.execute(f"""
            CREATE TABLE deps AS
            SELECT * FROM read_csv_auto('{deps_csv}', ignore_errors=true)
            WHERE Platform = 'Pypi'
        """)

        count = conn.execute("SELECT COUNT(*) FROM deps").fetchone()[0]
        print(f"[OK] Loaded {count:,} PyPI dependencies in {time.time()-t0:.1f}s")

        print("[...] Creating indexes on deps...")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_deps_project ON deps(Project_Name)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_deps_dependency ON deps(Dependency_Name)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_deps_dep_lower ON deps(LOWER(Dependency_Name))")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_deps_proj_lower ON deps(LOWER(Project_Name))")
        print("[OK] Dependency indexes created")
    else:
        if not with_deps:
            print("\n[SKIP] Dependencies table skipped (run with --with-deps to include)")
            print("       The projects table already has Dependents_Count — good enough for demo!")
        else:
            print("[WARN] Dependencies CSV not found — skipping")

    # --- Load Versions (filtered to PyPI) ---
    if versions_csv:
        print(f"\n[...] Loading versions from {versions_csv}")
        print("      Filtering to Platform='Pypi'...")
        t0 = time.time()

        conn.execute(f"""
            CREATE TABLE versions AS
            SELECT * FROM read_csv_auto('{versions_csv}', ignore_errors=true)
            WHERE Platform = 'Pypi'
        """)

        count = conn.execute("SELECT COUNT(*) FROM versions").fetchone()[0]
        print(f"[OK] Loaded {count:,} PyPI versions in {time.time()-t0:.1f}s")

        print("[...] Creating indexes on versions...")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_versions_project ON versions(Project_Name)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_versions_proj_lower ON versions(LOWER(Project_Name))")
        print("[OK] Version indexes created")
    else:
        print("[WARN] Versions CSV not found — skipping")

    # --- Summary ---
    print("\n" + "=" * 60)
    print("DATABASE LOADED SUCCESSFULLY")
    print("=" * 60)
    tables = conn.execute("SHOW TABLES").fetchall()
    for (table_name,) in tables:
        count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        print(f"  {table_name}: {count:,} rows")
    print(f"\nDatabase: {DB_PATH}")
    print(f"Size: {DB_PATH.stat().st_size / (1024**3):.2f} GB")

    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load Libraries.io data into DuckDB")
    parser.add_argument("--with-deps", action="store_true",
                        help="Also load the huge dependencies table (~30-40 min). Skip for fast setup.")
    parser.add_argument("--skip-extract", action="store_true",
                        help="Skip tar extraction (if CSVs already extracted)")
    args = parser.parse_args()

    if not args.skip_extract:
        extract_tar()
    load_data(with_deps=args.with_deps)
