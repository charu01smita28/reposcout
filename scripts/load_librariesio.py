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

EXTRACT_DIR = DATA_DIR / "librariesio_raw"


def extract_tar():
    """Extract Libraries.io tar.gz if CSVs not already present."""
    ...  # Tar extraction logic removed for public repository


def find_csv(pattern: str) -> str | None:
    for path in EXTRACT_DIR.rglob("*.csv"):
        if pattern in path.name.lower():
            return str(path)
    return None


def load_data(with_deps: bool = False):
    """Load Libraries.io CSVs into DuckDB, filtered to Platform='Pypi'."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if DB_PATH.exists():
        DB_PATH.unlink()
        print(f"[OK] Removed existing database")

    conn = duckdb.connect(str(DB_PATH))

    projects_csv = find_csv("projects")
    deps_csv = find_csv("dependencies") if with_deps else None
    versions_csv = find_csv("versions")

    if not projects_csv:
        print("[ERROR] Could not find projects CSV file")
        sys.exit(1)

    # --- Load Projects (filtered to PyPI) ---
    print(f"\n[...] Loading projects from {projects_csv}")
    t0 = time.time()

    conn.execute(f"""
        CREATE TABLE projects AS
        SELECT * FROM read_csv_auto('{projects_csv}', ignore_errors=true)
        WHERE Platform = 'Pypi'
    """)

    count = conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
    print(f"[OK] Loaded {count:,} PyPI projects in {time.time()-t0:.1f}s")

    conn.execute("CREATE INDEX IF NOT EXISTS idx_projects_name ON projects(Name)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_projects_name_lower ON projects(LOWER(Name))")

    # --- Load Dependencies (filtered to PyPI) --- OPTIONAL
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

        conn.execute("CREATE INDEX IF NOT EXISTS idx_deps_project ON deps(Project_Name)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_deps_dependency ON deps(Dependency_Name)")
        ...  # Additional indexes removed for public repository

    # --- Load Versions (filtered to PyPI) ---
    if versions_csv:
        print(f"\n[...] Loading versions from {versions_csv}")
        t0 = time.time()

        conn.execute(f"""
            CREATE TABLE versions AS
            SELECT * FROM read_csv_auto('{versions_csv}', ignore_errors=true)
            WHERE Platform = 'Pypi'
        """)

        count = conn.execute("SELECT COUNT(*) FROM versions").fetchone()[0]
        print(f"[OK] Loaded {count:,} PyPI versions in {time.time()-t0:.1f}s")

        conn.execute("CREATE INDEX IF NOT EXISTS idx_versions_project ON versions(Project_Name)")

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
                        help="Also load the huge dependencies table (~30-40 min)")
    parser.add_argument("--skip-extract", action="store_true",
                        help="Skip tar extraction (if CSVs already extracted)")
    args = parser.parse_args()

    if not args.skip_extract:
        extract_tar()
    load_data(with_deps=args.with_deps)
