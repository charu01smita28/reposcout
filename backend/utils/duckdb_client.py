import re

import duckdb
import pandas as pd
from backend.config import DUCKDB_PATH

_conn = None
_table_cache: dict[str, bool] = {}


def get_conn() -> duckdb.DuckDBPyConnection:
    global _conn
    if _conn is None:
        _conn = duckdb.connect(DUCKDB_PATH, read_only=True)
    return _conn


def has_table(name: str) -> bool:
    if name not in _table_cache:
        conn = get_conn()
        tables = [row[0] for row in conn.execute("SHOW TABLES").fetchall()]
        _table_cache[name] = name in tables
    return _table_cache[name]


# ---------------------------------------------------------------------------
# Dataset stats
# ---------------------------------------------------------------------------

def get_dataset_stats() -> dict:
    conn = get_conn()
    pkg_count = 0
    dep_count = 0

    if has_table("packages"):
        pkg_count = conn.execute("SELECT COUNT(*) FROM packages").fetchone()[0]
    if has_table("lib_deps"):
        dep_count = conn.execute("SELECT COUNT(*) FROM lib_deps").fetchone()[0]

    return {"total_packages": pkg_count, "total_dependencies": dep_count}


# ---------------------------------------------------------------------------
# Package lookups (Layer 2 primary, Layer 1 fallback)
# ---------------------------------------------------------------------------

def get_package(package_name: str) -> dict | None:
    conn = get_conn()

    # Try unified packages table first (Layer 2)
    if has_table("packages"):
        row = conn.execute(
            "SELECT * FROM packages WHERE LOWER(package_name) = LOWER(?) LIMIT 1",
            [package_name],
        ).fetchdf()
        if not row.empty:
            return row.iloc[0].to_dict()

    # Fallback to lib_projects (Layer 1)
    if has_table("lib_projects"):
        row = conn.execute(
            "SELECT * FROM lib_projects WHERE LOWER(Name) = LOWER(?) LIMIT 1",
            [package_name],
        ).fetchdf()
        if not row.empty:
            return row.iloc[0].to_dict()

    return None


def get_dependents_count(package_name: str) -> int:
    conn = get_conn()

    # Layer 2: fresh dependent count
    if has_table("packages"):
        result = conn.execute(
            "SELECT dependent_count FROM packages WHERE LOWER(package_name) = LOWER(?)",
            [package_name],
        ).fetchone()
        if result and result[0]:
            return int(result[0])

    # Layer 1: count from dependency graph
    if has_table("lib_deps"):
        result = conn.execute(
            "SELECT COUNT(*) FROM lib_deps WHERE LOWER(Dependency_Name) = LOWER(?)",
            [package_name],
        ).fetchone()
        return result[0] if result else 0

    # Layer 1: pre-computed column
    if has_table("lib_projects"):
        result = conn.execute(
            "SELECT Dependents_Count FROM lib_projects WHERE LOWER(Name) = LOWER(?)",
            [package_name],
        ).fetchone()
        return int(result[0] or 0) if result else 0

    return 0


# ---------------------------------------------------------------------------
# Health metrics (merged from all layers)
# ---------------------------------------------------------------------------

def get_health_metrics(package_name: str) -> dict | None:
    conn = get_conn()
    result = {}

    # Layer 2: fresh data
    if has_table("packages"):
        row = conn.execute(
            "SELECT * FROM packages WHERE LOWER(package_name) = LOWER(?) LIMIT 1",
            [package_name],
        ).fetchdf()
        if not row.empty:
            r = row.iloc[0].to_dict()
            result.update({
                "Name": r.get("package_name", package_name),
                "Stars": r.get("stars", 0),
                "Forks": r.get("forks", 0),
                "Dependents_Count": r.get("dependent_count", 0),
                "actual_dependents": r.get("dependent_count", 0),
                "open_issues": r.get("open_issues", 0),
                "Repository_URL": r.get("github_repo", ""),
                "Description": r.get("description", ""),
                "growth_pct": r.get("growth_pct", 0),
            })

    # Layer 1: supplement with historical data
    if has_table("lib_projects"):
        row = conn.execute(
            "SELECT * FROM lib_projects WHERE LOWER(Name) = LOWER(?) LIMIT 1",
            [package_name],
        ).fetchdf()
        if not row.empty:
            r = row.iloc[0].to_dict()
            # Only fill in what Layer 2 didn't provide
            result.setdefault("Name", r.get("Name", package_name))
            result.setdefault("Stars", r.get("Stars", 0))
            result.setdefault("Forks", r.get("Forks", 0))
            result.setdefault("Dependents_Count", r.get("Dependents_Count", 0))
            result.setdefault("Repository_URL", r.get("Repository_URL", ""))
            result.setdefault("Description", r.get("Description", ""))
            result["Licenses"] = r.get("Licenses", "")
            result["Latest_Release_Publish_Timestamp"] = r.get("Latest_Release_Publish_Timestamp", "")

    # Version count from Layer 1
    if has_table("lib_versions"):
        ver_count = conn.execute(
            "SELECT COUNT(*) FROM lib_versions WHERE LOWER(Project_Name) = LOWER(?)",
            [package_name],
        ).fetchone()
        result["total_versions"] = ver_count[0] if ver_count else 0
    else:
        result.setdefault("total_versions", 0)

    return result if result else None


# ---------------------------------------------------------------------------
# Dependency graph (Layer 1 only)
# ---------------------------------------------------------------------------

def get_dependency_tree(package_name: str, limit: int = 50) -> list[dict]:
    if not has_table("lib_deps"):
        return []
    conn = get_conn()
    df = conn.execute(
        """
        SELECT Dependency_Name, Dependency_Kind, Dependency_Requirements
        FROM lib_deps
        WHERE LOWER(Project_Name) = LOWER(?)
        LIMIT ?
        """,
        [package_name, limit],
    ).fetchdf()
    return df.to_dict(orient="records")


def get_reverse_dependencies(package_name: str, limit: int = 50) -> list[dict]:
    if not has_table("lib_deps"):
        return []
    conn = get_conn()
    df = conn.execute(
        """
        SELECT Project_Name, Dependency_Kind, Dependency_Requirements
        FROM lib_deps
        WHERE LOWER(Dependency_Name) = LOWER(?)
        LIMIT ?
        """,
        [package_name, limit],
    ).fetchdf()
    return df.to_dict(orient="records")


# ---------------------------------------------------------------------------
# Comparisons
# ---------------------------------------------------------------------------

def compare_packages(pkg_names: list[str]) -> pd.DataFrame:
    conn = get_conn()

    if has_table("packages"):
        placeholders = ",".join(["LOWER(?)"] * len(pkg_names))
        df = conn.execute(
            f"""
            SELECT
                package_name AS Name,
                description AS Description,
                stars AS Stars,
                forks AS Forks,
                dependent_count AS Dependents_Count,
                github_repo AS Repository_URL,
                open_issues,
                dependent_count AS actual_dependents
            FROM packages
            WHERE LOWER(package_name) IN ({placeholders})
            ORDER BY dependent_count DESC
            """,
            [n.lower() for n in pkg_names],
        ).fetchdf()
        if not df.empty:
            return df

    # Fallback to lib_projects
    if has_table("lib_projects"):
        placeholders = ",".join(["LOWER(?)"] * len(pkg_names))
        df = conn.execute(
            f"""
            SELECT
                Name, Description, Stars, Forks, Dependents_Count,
                Repository_URL, Licenses,
                Dependents_Count AS actual_dependents
            FROM lib_projects
            WHERE LOWER(Name) IN ({placeholders})
            """,
            [n.lower() for n in pkg_names],
        ).fetchdf()
        return df

    return pd.DataFrame()


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

def search_packages_by_keyword(keyword: str, limit: int = 20) -> list[dict]:
    conn = get_conn()

    if has_table("packages"):
        df = conn.execute(
            """
            SELECT package_name AS Name, description AS Description,
                   stars AS Stars, dependent_count AS Dependents_Count,
                   github_repo AS Repository_URL
            FROM packages
            WHERE LOWER(description) LIKE LOWER(?)
            ORDER BY dependent_count DESC
            LIMIT ?
            """,
            [f"%{keyword}%", limit],
        ).fetchdf()
        if not df.empty:
            return df.to_dict(orient="records")

    if has_table("lib_projects"):
        df = conn.execute(
            """
            SELECT Name, Description, Stars, Dependents_Count, Repository_URL
            FROM lib_projects
            WHERE LOWER(Description) LIKE LOWER(?)
            ORDER BY Dependents_Count DESC
            LIMIT ?
            """,
            [f"%{keyword}%", limit],
        ).fetchdf()
        return df.to_dict(orient="records")

    return []


def get_top_packages_for_names(names: list[str]) -> pd.DataFrame:
    if not names:
        return pd.DataFrame()
    conn = get_conn()

    if has_table("packages"):
        placeholders = ",".join(["LOWER(?)"] * len(names))
        df = conn.execute(
            f"""
            SELECT
                package_name AS Name,
                description AS Description,
                stars AS Stars,
                forks AS Forks,
                dependent_count AS Dependents_Count,
                github_repo AS Repository_URL,
                dependent_count AS actual_dependents
            FROM packages
            WHERE LOWER(package_name) IN ({placeholders})
            ORDER BY dependent_count DESC
            """,
            [n.lower() for n in names],
        ).fetchdf()
        if not df.empty:
            return df

    return pd.DataFrame()


# ---------------------------------------------------------------------------
# Download history (daily → monthly aggregation)
# ---------------------------------------------------------------------------

def get_download_history(package_names: list[str]) -> list[dict]:
    if not package_names or not has_table("download_stats"):
        return []
    conn = get_conn()
    placeholders = ",".join(["LOWER(?)"] * len(package_names))
    df = conn.execute(
        f"""
        SELECT
            package_name,
            STRFTIME(DATE_TRUNC('month', CAST(month AS DATE)), '%Y-%m') AS month,
            SUM(downloads) AS downloads
        FROM download_stats
        WHERE LOWER(package_name) IN ({placeholders})
        GROUP BY package_name, DATE_TRUNC('month', CAST(month AS DATE))
        ORDER BY month, package_name
        """,
        [n.lower() for n in package_names],
    ).fetchdf()
    if df.empty:
        return []
    return df.to_dict(orient="records")


# ---------------------------------------------------------------------------
# Code snippet extraction from README
# ---------------------------------------------------------------------------

# Matches ```python or ```py tagged blocks (case-insensitive)
_PYTHON_FENCED_RE = re.compile(
    r"```(?:python|py)\s*\n(.*?)```",
    re.DOTALL | re.IGNORECASE,
)

# Matches any fenced code block (fallback)
_ANY_FENCED_RE = re.compile(
    r"```(\w*)\s*\n(.*?)```",
    re.DOTALL,
)

_INDENTED_RE = re.compile(
    r"(?:^|\n)((?:(?:    |\t).+\n?){2,})",
)

_PIP_ONLY_RE = re.compile(r"^\s*(\$\s*)?(pip\s+install\s+\S+|python\s+-m\s+pip\s+install\s+\S+)\s*$")

# Language tags that indicate non-Python code content
_SKIP_LANGS = {"html", "xml", "css", "json", "yaml", "yml", "toml", "ini", "console", "bash", "sh", "shell", "sql"}


def _is_trivial_install(code: str) -> bool:
    """Return True if every non-blank line is just a pip install command."""
    lines = [l for l in code.strip().splitlines() if l.strip()]
    return all(_PIP_ONLY_RE.match(l) for l in lines) if lines else True


_CODE_SIGNALS_RE = re.compile(
    r"(^import |^from .+ import |^def |^class |^>>> |[=()\[\]{}]|^\w+\.)",
    re.MULTILINE,
)


def _looks_like_code(code: str, strict: bool = False) -> bool:
    """Return True if the text looks like actual code, not prose or HTML."""
    first_line = code.split("\n")[0].strip()
    if first_line.startswith("<") and ">" in first_line:
        return False  # HTML
    # Skip markdown prose (bold, links, etc.)
    if "**" in first_line or first_line.startswith("[") or first_line.startswith("*"):
        return False
    # In strict mode (for indented blocks), require Python-like syntax
    if strict and not _CODE_SIGNALS_RE.search(code):
        return False
    return True


def get_code_snippet(package_name: str) -> dict | None:
    """Extract the first meaningful code block from a package's README."""
    if not has_table("pypi_metadata"):
        return None

    conn = get_conn()
    row = conn.execute(
        "SELECT description FROM pypi_metadata WHERE LOWER(name) = LOWER(?) LIMIT 1",
        [package_name],
    ).fetchone()

    if not row or not row[0]:
        return None

    readme = row[0]

    # Priority 1: explicitly Python-tagged fenced blocks
    for m in _PYTHON_FENCED_RE.finditer(readme):
        code = m.group(1).strip()
        if code and not _is_trivial_install(code) and _looks_like_code(code):
            return {"code": code, "source": "README"}

    # Priority 2: untagged fenced blocks that look like code
    for m in _ANY_FENCED_RE.finditer(readme):
        lang = m.group(1).lower()
        if lang in _SKIP_LANGS:
            continue
        code = m.group(2).strip()
        if code and not _is_trivial_install(code) and _looks_like_code(code):
            return {"code": code, "source": "README"}

    # Priority 3: indented code blocks (RST style) — strict check
    for m in _INDENTED_RE.finditer(readme):
        code = "\n".join(l[4:] if l.startswith("    ") else l[1:] for l in m.group(1).splitlines())
        code = code.strip()
        if code and not _is_trivial_install(code) and _looks_like_code(code, strict=True):
            return {"code": code, "source": "README"}

    return None
