import duckdb
import pandas as pd
from backend.config import DUCKDB_PATH

_conn = None
_has_deps = None
_has_versions = None


def get_conn() -> duckdb.DuckDBPyConnection:
    global _conn
    if _conn is None:
        _conn = duckdb.connect(DUCKDB_PATH, read_only=True)
    return _conn


def has_table(table_name: str) -> bool:
    conn = get_conn()
    tables = [row[0] for row in conn.execute("SHOW TABLES").fetchall()]
    return table_name in tables


def has_deps_table() -> bool:
    global _has_deps
    if _has_deps is None:
        _has_deps = has_table("deps")
    return _has_deps


def has_versions_table() -> bool:
    global _has_versions
    if _has_versions is None:
        _has_versions = has_table("versions")
    return _has_versions


def get_dataset_stats() -> dict:
    conn = get_conn()
    try:
        pkg_count = conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
    except Exception:
        pkg_count = 0
    dep_count = 0
    if has_deps_table():
        try:
            dep_count = conn.execute("SELECT COUNT(*) FROM deps").fetchone()[0]
        except Exception:
            pass
    return {"total_packages": pkg_count, "total_dependencies": dep_count}


def get_package(package_name: str) -> dict | None:
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM projects WHERE LOWER(Name) = LOWER(?) LIMIT 1",
        [package_name],
    ).fetchdf()
    if row.empty:
        return None
    return row.iloc[0].to_dict()


def get_dependents_count(package_name: str) -> int:
    # If deps table exists, count from there; otherwise use pre-computed column
    if has_deps_table():
        conn = get_conn()
        result = conn.execute(
            "SELECT COUNT(*) FROM deps WHERE LOWER(Dependency_Name) = LOWER(?)",
            [package_name],
        ).fetchone()
        return result[0] if result else 0
    else:
        pkg = get_package(package_name)
        return int(pkg.get("Dependents_Count", 0) or 0) if pkg else 0


def get_dependency_tree(package_name: str, limit: int = 50) -> list[dict]:
    if not has_deps_table():
        return []
    conn = get_conn()
    df = conn.execute(
        """
        SELECT Dependency_Name, Dependency_Kind, Dependency_Requirements
        FROM deps
        WHERE LOWER(Project_Name) = LOWER(?)
        LIMIT ?
        """,
        [package_name, limit],
    ).fetchdf()
    return df.to_dict(orient="records")


def get_reverse_dependencies(package_name: str, limit: int = 50) -> list[dict]:
    if not has_deps_table():
        return []
    conn = get_conn()
    df = conn.execute(
        """
        SELECT Project_Name, Dependency_Kind, Dependency_Requirements
        FROM deps
        WHERE LOWER(Dependency_Name) = LOWER(?)
        LIMIT ?
        """,
        [package_name, limit],
    ).fetchdf()
    return df.to_dict(orient="records")


def compare_packages(pkg_names: list[str]) -> pd.DataFrame:
    conn = get_conn()
    placeholders = ",".join(["LOWER(?)"] * len(pkg_names))

    if has_deps_table():
        deps_subquery = "(SELECT COUNT(*) FROM deps d WHERE LOWER(d.Dependency_Name) = LOWER(p.Name)) AS actual_dependents"
    else:
        deps_subquery = "p.Dependents_Count AS actual_dependents"

    df = conn.execute(
        f"""
        SELECT
            p.Name,
            p.Description,
            p.Stars,
            p.Forks,
            p.Dependents_Count,
            p.Latest_Release_Number,
            p.Latest_Release_Publish_Timestamp,
            p.Repository_URL,
            p.Homepage_URL,
            p.Licenses,
            {deps_subquery}
        FROM projects p
        WHERE LOWER(p.Name) IN ({placeholders})
        """,
        [n.lower() for n in pkg_names],
    ).fetchdf()
    return df


def get_health_metrics(package_name: str) -> dict | None:
    conn = get_conn()

    if has_deps_table():
        deps_subquery = "(SELECT COUNT(*) FROM deps d WHERE LOWER(d.Dependency_Name) = LOWER(p.Name)) AS actual_dependents"
    else:
        deps_subquery = "p.Dependents_Count AS actual_dependents"

    if has_versions_table():
        versions_subquery = "(SELECT COUNT(*) FROM versions v WHERE LOWER(v.Project_Name) = LOWER(p.Name) AND v.Platform = 'Pypi') AS total_versions"
    else:
        versions_subquery = "0 AS total_versions"

    row = conn.execute(
        f"""
        SELECT
            p.Name,
            p.Stars,
            p.Forks,
            p.Dependents_Count,
            p.Latest_Release_Publish_Timestamp,
            p.Repository_URL,
            p.Licenses,
            {versions_subquery},
            {deps_subquery}
        FROM projects p
        WHERE LOWER(p.Name) = LOWER(?)
        LIMIT 1
        """,
        [package_name],
    ).fetchdf()
    if row.empty:
        return None
    return row.iloc[0].to_dict()


def search_packages_by_keyword(keyword: str, limit: int = 20) -> list[dict]:
    conn = get_conn()
    df = conn.execute(
        """
        SELECT Name, Description, Stars, Dependents_Count, Repository_URL
        FROM projects
        WHERE LOWER(Description) LIKE LOWER(?)
        ORDER BY Dependents_Count DESC
        LIMIT ?
        """,
        [f"%{keyword}%", limit],
    ).fetchdf()
    return df.to_dict(orient="records")


def get_top_packages_for_names(names: list[str]) -> pd.DataFrame:
    if not names:
        return pd.DataFrame()
    conn = get_conn()
    placeholders = ",".join(["LOWER(?)"] * len(names))

    if has_deps_table():
        deps_subquery = "(SELECT COUNT(*) FROM deps d WHERE LOWER(d.Dependency_Name) = LOWER(p.Name)) AS actual_dependents"
    else:
        deps_subquery = "p.Dependents_Count AS actual_dependents"

    df = conn.execute(
        f"""
        SELECT
            p.Name,
            p.Description,
            p.Stars,
            p.Forks,
            p.Dependents_Count,
            p.Latest_Release_Publish_Timestamp,
            p.Repository_URL,
            {deps_subquery}
        FROM projects p
        WHERE LOWER(p.Name) IN ({placeholders})
        ORDER BY actual_dependents DESC
        """,
        [n.lower() for n in names],
    ).fetchdf()
    return df
