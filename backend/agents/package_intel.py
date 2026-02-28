from backend.utils.duckdb_client import (
    get_package,
    get_dependents_count,
    get_health_metrics,
    compare_packages as db_compare,
    search_packages_by_keyword,
    get_top_packages_for_names,
)
from backend.utils.qdrant_client import semantic_search_packages
from backend.utils.pypi_client import get_pypi_metadata, days_since_release
from backend.utils.scoring import compute_reposcout_score, get_score_label, get_score_color


def search_packages(query: str, limit: int = 20) -> dict:
    # Try semantic search first (Qdrant)
    try:
        semantic_results = semantic_search_packages(query, limit=limit)
    except Exception:
        semantic_results = []

    # Fallback / supplement with keyword search in DuckDB
    keyword_results = search_packages_by_keyword(query, limit=limit)

    # Merge: semantic results first, then keyword results not already present
    seen = set()
    merged = []
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

    return {
        "query": query,
        "total_found": len(merged),
        "packages": merged[:limit],
    }


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
