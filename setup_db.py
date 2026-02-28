"""
RepoScout Database Setup — Three-Layer Architecture

Builds reposcout.db from:
  Layer 1: Libraries.io 2020 data (historical dependency graph)
  Layer 2: BigQuery deps.dev exports (fresh ecosystem snapshot)

Usage:
    python setup_db.py                     # Layer 2 only (fast, ~1 min)
    python setup_db.py --with-layer1       # Both layers (~5 min without deps)
    python setup_db.py --with-layer1 --with-deps  # Everything (~30-40 min)

Expects CSVs in:
    data/layer1/  — Libraries.io CSVs (extracted from tar.gz)
    data/layer2/  — BigQuery CSV exports (dependents.csv, projects.csv, bridge.csv)
"""

import argparse
import sys
import time
import tarfile
import duckdb
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "reposcout.db"
LAYER1_DIR = DATA_DIR / "layer1"
LAYER2_DIR = DATA_DIR / "layer2"

TAR_PATH = Path("/Users/charusmitadhiman/Downloads/libraries.tar.gz")


def find_csv(directory: Path, pattern: str) -> str | None:
    for path in directory.rglob("*.csv"):
        if pattern in path.name.lower():
            return str(path)
    return None


def extract_tar():
    if LAYER1_DIR.exists() and any(LAYER1_DIR.rglob("*.csv")):
        print(f"[OK] Layer 1 CSVs already present in {LAYER1_DIR}")
        return

    if not TAR_PATH.exists():
        print(f"[ERROR] Tar file not found at {TAR_PATH}")
        print("  Update TAR_PATH in this script or extract manually into data/layer1/")
        sys.exit(1)

    print(f"[...] Extracting {TAR_PATH} → {LAYER1_DIR}")
    print("      This may take a while for 25GB...")
    LAYER1_DIR.mkdir(parents=True, exist_ok=True)

    with tarfile.open(TAR_PATH, "r:gz") as tar:
        tar.extractall(path=LAYER1_DIR)

    print("[OK] Extraction complete")


def load_layer2(db: duckdb.DuckDBPyConnection):
    """Load BigQuery exports — fresh ecosystem snapshot."""
    print("\n" + "=" * 60)
    print("LAYER 2 — Fresh Ecosystem Snapshot (BigQuery/deps.dev)")
    print("=" * 60)

    dependents_csv = find_csv(LAYER2_DIR, "dependents")
    bridge_csv = find_csv(LAYER2_DIR, "bridge")
    projects_csv = find_csv(LAYER2_DIR, "projects")

    if not dependents_csv:
        print("[ERROR] data/layer2/dependents.csv not found")
        print("  Export from BigQuery and place in data/layer2/")
        return False

    # Fresh dependent counts
    print(f"\n[...] Loading fresh dependents from {dependents_csv}")
    t0 = time.time()
    db.execute(f"""
        CREATE TABLE fresh_dependents AS
        SELECT * FROM read_csv_auto('{dependents_csv}', ignore_errors=true)
    """)
    count = db.execute("SELECT COUNT(*) FROM fresh_dependents").fetchone()[0]
    print(f"[OK] {count:,} packages in {time.time()-t0:.1f}s")

    # Bridge (PyPI → GitHub mapping)
    if bridge_csv:
        print(f"\n[...] Loading bridge from {bridge_csv}")
        t0 = time.time()
        db.execute(f"""
            CREATE TABLE bridge AS
            SELECT * FROM read_csv_auto('{bridge_csv}', ignore_errors=true)
        """)
        count = db.execute("SELECT COUNT(*) FROM bridge").fetchone()[0]
        print(f"[OK] {count:,} mappings in {time.time()-t0:.1f}s")
    else:
        print("[WARN] bridge.csv not found — skipping")

    # GitHub project metadata
    if projects_csv:
        print(f"\n[...] Loading GitHub projects from {projects_csv}")
        t0 = time.time()
        db.execute(f"""
            CREATE TABLE github_projects AS
            SELECT * FROM read_csv_auto('{projects_csv}', ignore_errors=true)
        """)
        count = db.execute("SELECT COUNT(*) FROM github_projects").fetchone()[0]
        print(f"[OK] {count:,} projects in {time.time()-t0:.1f}s")
    else:
        print("[WARN] projects.csv not found — skipping")

    # Unified packages view (the main table agents query)
    print("\n[...] Creating unified 'packages' table...")
    t0 = time.time()

    join_parts = ["FROM fresh_dependents d"]
    select_parts = [
        "d.package_name",
        "d.dependent_count",
    ]

    if bridge_csv:
        join_parts.append("LEFT JOIN bridge b ON b.package_name = d.package_name")
        select_parts.append("b.github_repo")
    else:
        select_parts.append("NULL AS github_repo")

    if projects_csv and bridge_csv:
        join_parts.append("LEFT JOIN github_projects g ON g.Name = b.github_repo")
        select_parts.extend([
            "g.StarsCount AS stars",
            "g.ForksCount AS forks",
            "g.OpenIssuesCount AS open_issues",
            "g.Description AS description",
            "g.Homepage AS homepage",
        ])
    else:
        select_parts.extend([
            "0 AS stars",
            "0 AS forks",
            "0 AS open_issues",
            "NULL AS description",
            "NULL AS homepage",
        ])

    query = f"""
        CREATE TABLE packages AS
        SELECT {', '.join(select_parts)}
        {' '.join(join_parts)}
        ORDER BY d.dependent_count DESC
    """
    db.execute(query)
    count = db.execute("SELECT COUNT(*) FROM packages").fetchone()[0]
    print(f"[OK] Unified 'packages' table: {count:,} rows in {time.time()-t0:.1f}s")

    # Indexes
    print("[...] Creating indexes on packages...")
    db.execute("CREATE INDEX IF NOT EXISTS idx_pkg_name ON packages(package_name)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_pkg_name_lower ON packages(LOWER(package_name))")
    db.execute("CREATE INDEX IF NOT EXISTS idx_pkg_deps ON packages(dependent_count DESC)")
    print("[OK] Indexes created")

    return True


def load_layer1(db: duckdb.DuckDBPyConnection, with_deps: bool = False):
    """Load Libraries.io data — historical dependency graph."""
    print("\n" + "=" * 60)
    print("LAYER 1 — Historical Dependency Graph (Libraries.io 2020)")
    print("=" * 60)

    projects_csv = find_csv(LAYER1_DIR, "projects")
    versions_csv = find_csv(LAYER1_DIR, "versions")
    deps_csv = find_csv(LAYER1_DIR, "dependencies") if with_deps else None

    if not projects_csv:
        print("[ERROR] No projects CSV found in data/layer1/")
        print(f"  Searched: {LAYER1_DIR}")
        return False

    # Projects
    print(f"\n[...] Loading lib_projects from {projects_csv}")
    print("      Filtering to Platform='Pypi'...")
    t0 = time.time()
    db.execute(f"""
        CREATE TABLE lib_projects AS
        SELECT * FROM read_csv_auto('{projects_csv}', ignore_errors=true)
        WHERE Platform = 'Pypi'
    """)
    count = db.execute("SELECT COUNT(*) FROM lib_projects").fetchone()[0]
    print(f"[OK] {count:,} PyPI projects in {time.time()-t0:.1f}s")

    db.execute("CREATE INDEX IF NOT EXISTS idx_libproj_name ON lib_projects(Name)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_libproj_lower ON lib_projects(LOWER(Name))")

    # Versions
    if versions_csv:
        print(f"\n[...] Loading lib_versions from {versions_csv}")
        print("      Filtering to Platform='Pypi'...")
        t0 = time.time()
        db.execute(f"""
            CREATE TABLE lib_versions AS
            SELECT * FROM read_csv_auto('{versions_csv}', ignore_errors=true)
            WHERE Platform = 'Pypi'
        """)
        count = db.execute("SELECT COUNT(*) FROM lib_versions").fetchone()[0]
        print(f"[OK] {count:,} PyPI versions in {time.time()-t0:.1f}s")

        db.execute("CREATE INDEX IF NOT EXISTS idx_libver_proj ON lib_versions(Project_Name)")
    else:
        print("[WARN] Versions CSV not found — skipping")

    # Dependencies (optional, the big one)
    if deps_csv:
        print(f"\n[...] Loading lib_deps from {deps_csv}")
        print("      Filtering to Platform='Pypi'... (235M rows, be patient)")
        t0 = time.time()
        db.execute(f"""
            CREATE TABLE lib_deps AS
            SELECT * FROM read_csv_auto('{deps_csv}', ignore_errors=true)
            WHERE Platform = 'Pypi'
        """)
        count = db.execute("SELECT COUNT(*) FROM lib_deps").fetchone()[0]
        print(f"[OK] {count:,} PyPI dependencies in {time.time()-t0:.1f}s")

        print("[...] Creating indexes on lib_deps...")
        db.execute("CREATE INDEX IF NOT EXISTS idx_libdeps_proj ON lib_deps(Project_Name)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_libdeps_dep ON lib_deps(Dependency_Name)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_libdeps_dep_lower ON lib_deps(LOWER(Dependency_Name))")
        print("[OK] Dependency indexes created")
    else:
        if not with_deps:
            print("\n[SKIP] lib_deps skipped (run with --with-deps to include)")
        else:
            print("[WARN] Dependencies CSV not found")

    return True


def print_summary(db: duckdb.DuckDBPyConnection):
    print("\n" + "=" * 60)
    print("DATABASE READY")
    print("=" * 60)
    tables = db.execute("SHOW TABLES").fetchall()
    for (table_name,) in tables:
        count = db.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        print(f"  {table_name}: {count:,} rows")

    print(f"\n  Database: {DB_PATH}")
    print(f"  Size: {DB_PATH.stat().st_size / (1024**2):.1f} MB")

    # Sample from packages
    print("\n  Sample from 'packages' table:")
    sample = db.execute("SELECT package_name, dependent_count, stars FROM packages LIMIT 5").fetchdf()
    print(sample.to_string(index=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build RepoScout database")
    parser.add_argument("--with-layer1", action="store_true",
                        help="Load Libraries.io historical data (Layer 1)")
    parser.add_argument("--with-deps", action="store_true",
                        help="Include the huge dependencies table from Layer 1 (~30-40 min)")
    parser.add_argument("--extract", action="store_true",
                        help="Extract tar.gz before loading Layer 1")
    args = parser.parse_args()

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Remove existing DB
    if DB_PATH.exists():
        DB_PATH.unlink()
        print(f"[OK] Removed existing {DB_PATH.name}")

    db = duckdb.connect(str(DB_PATH))

    # Layer 2 always loads (it's fast and primary)
    layer2_ok = load_layer2(db)

    # Layer 1 optional
    if args.with_layer1:
        if args.extract:
            extract_tar()
        load_layer1(db, with_deps=args.with_deps)

    print_summary(db)
    db.close()

    print("\nDone! Your agents can now query reposcout.db")
    print("  db = duckdb.connect('data/reposcout.db')")
    print("  db.execute(\"SELECT * FROM packages WHERE package_name = ?\", ['fastapi']).fetchdf()")
