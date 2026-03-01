import re

from backend.utils.duckdb_client import (
    get_package,
    get_dependents_count,
    get_health_metrics,
    get_code_snippet,
    compare_packages as db_compare,
    search_packages_by_keyword,
    get_top_packages_for_names,
    get_conn,
    has_table,
)
from backend.utils.qdrant_client import semantic_search_packages
from backend.utils.pypi_client import get_pypi_metadata, days_since_release
from backend.utils.scoring import compute_reposcout_score, get_score_label, get_score_color


_GROWTH_PATTERN = re.compile(
    r"(grow|trend|rising|fastest|hottest|explod|surge|boom|popular|emerging)",
    re.IGNORECASE,
)


def _get_top_growth_packages(limit: int = 20) -> list[dict]:
    """Get top packages by growth_pct from DuckDB, filtering out junk."""
    if not has_table("packages"):
        return []
    conn = get_conn()
    # Require real packages: decent deps AND some GitHub presence
    # Sort by growth * log(deps) to balance explosive growth with real adoption
    rows = conn.execute("""
        SELECT package_name, description, stars, dependent_count, growth_pct
        FROM packages
        WHERE growth_pct > 50
          AND dependent_count >= 50
          AND (COALESCE(stars, 0) > 0 OR dependent_count >= 500)
        ORDER BY growth_pct * LN(dependent_count + 1) DESC
        LIMIT ?
    """, [limit]).fetchall()
    return [
        {
            "name": r[0],
            "description": r[1] or "",
            "stars": r[2] or 0,
            "dependents_count": r[3] or 0,
            "growth_pct": r[4] or 0,
            "score": 0,
        }
        for r in rows
    ]


def search_packages(query: str, limit: int = 20) -> dict:
    # Try semantic search first (Qdrant)
    try:
        semantic_results = semantic_search_packages(query, limit=limit)
    except Exception:
        semantic_results = []

    # Fallback / supplement with keyword search in DuckDB
    keyword_results = search_packages_by_keyword(query, limit=limit)

    # If query is about growth/trending, supplement with top growth packages
    growth_results = []
    if _GROWTH_PATTERN.search(query):
        growth_results = _get_top_growth_packages(limit=limit)

    # For growth queries: growth results first, then semantic
    # For normal queries: semantic first, then keyword
    is_growth_query = bool(growth_results)

    seen = set()
    merged = []

    if is_growth_query:
        # Growth results first — they're the actual answer
        for r in growth_results:
            name = r["name"].lower()
            if name not in seen:
                seen.add(name)
                merged.append(r)

    for r in semantic_results:
        name = r["name"].lower()
        if name not in seen:
            seen.add(name)
            merged.append(r)
    for r in keyword_results:
        name = r["Name"].lower() if "Name" in r else r.get("name", "").lower()
        if name and name not in seen:
            seen.add(name)
            merged.append({
                "name": r.get("Name", r.get("name", "")),
                "description": r.get("Description", r.get("description", "")),
                "stars": r.get("Stars", r.get("stars", 0)),
                "dependents_count": r.get("Dependents_Count", r.get("dependents_count", 0)),
                "score": 0,
            })

    result = {
        "query": query,
        "total_found": len(merged),
        "packages": merged[:limit],
    }

    # For growth queries, add explicit top-growth hint so the LLM picks the right packages
    if is_growth_query:
        top_growth = sorted(
            [p for p in merged if p.get("growth_pct", 0)],
            key=lambda p: p.get("growth_pct", 0),
            reverse=True,
        )[:7]
        result["top_by_growth"] = [
            {"name": p["name"], "growth_pct": p.get("growth_pct", 0)}
            for p in top_growth
        ]

    return result


async def get_package_stats(package_name: str) -> dict:
    # Get from DuckDB
    metrics = get_health_metrics(package_name)

    # Supplement with PyPI for fresh data
    pypi_data = await get_pypi_metadata(package_name)

    if not metrics and not pypi_data:
        return {"error": f"Package '{package_name}' not found in database or PyPI"}

    # Build unified stats
    stats = {
        "name": package_name,
        "found_in_db": metrics is not None,
        "found_in_pypi": pypi_data is not None,
    }

    if metrics:
        stats.update({
            "stars": metrics.get("Stars", 0),
            "forks": metrics.get("Forks", 0),
            "dependents_count": metrics.get("actual_dependents", metrics.get("Dependents_Count", 0)),
            "total_versions": metrics.get("total_versions", 0),
            "repository_url": metrics.get("Repository_URL", ""),
            "license": metrics.get("Licenses", ""),
            "growth_pct": metrics.get("growth_pct", 0),
        })

    if pypi_data:
        stats.update({
            "latest_version": pypi_data.get("version", ""),
            "summary": pypi_data.get("summary", ""),
            "author": pypi_data.get("author", ""),
            "pypi_license": pypi_data.get("license", ""),
            "pypi_total_versions": pypi_data.get("total_versions", 0),
            "latest_release_date": pypi_data.get("latest_release_date", ""),
            "requires_dist": pypi_data.get("requires_dist", []),
        })
        # Use PyPI versions if DB doesn't have them
        if not stats.get("total_versions"):
            stats["total_versions"] = pypi_data.get("total_versions", 0)

    # Compute health score
    days = days_since_release(stats.get("latest_release_date") or metrics.get("Latest_Release_Publish_Timestamp"))
    score_input = {
        "dependents_count": stats.get("dependents_count", 0),
        "stars": stats.get("stars", 0),
        "days_since_last_release": days,
        "total_versions": stats.get("total_versions", 0),
        "forks": stats.get("forks", 0),
    }
    score = compute_reposcout_score(score_input)
    stats["reposcout_score"] = score
    stats["score_label"] = get_score_label(score)
    stats["score_color"] = get_score_color(score)
    stats["days_since_last_release"] = days

    # Code snippet from README
    snippet = get_code_snippet(package_name)
    if snippet:
        stats["code_snippet"] = snippet["code"]
        stats["code_source"] = snippet["source"]

    return stats


def get_dependents(package_name: str) -> dict:
    count = get_dependents_count(package_name)
    return {
        "package_name": package_name,
        "dependents_count": count,
    }


async def compare_packages_intel(package_names: list[str]) -> dict:
    results = []
    for name in package_names:
        stats = await get_package_stats(name)
        results.append(stats)

    # Sort by dependents count (highest first)
    results.sort(key=lambda x: x.get("dependents_count", 0), reverse=True)

    return {
        "packages": results,
        "comparison_count": len(results),
    }
