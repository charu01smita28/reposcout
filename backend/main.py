from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from backend.models import SearchRequest
from backend.agents.orchestrator import run_agent
from backend.agents.package_intel import get_package_stats, compare_packages_intel, search_packages
from backend.utils.duckdb_client import get_dataset_stats, get_dependents_count, get_dependency_tree, get_reverse_dependencies, get_download_history
from backend.utils.scoring import get_score_label, get_score_color

app = FastAPI(title="RepoScout API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Routes ---

@app.get("/api/stats")
async def dataset_stats():
    stats = get_dataset_stats()
    return {
        "total_packages": stats["total_packages"],
        "total_dependencies": stats["total_dependencies"],
        "platforms": ["PyPI"],
    }


@app.post("/api/search")
async def search(req: SearchRequest):
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    result = await run_agent(req.query, mode=req.mode)
    return result


@app.get("/api/package/{package_name}")
async def package_detail(package_name: str):
    stats = await get_package_stats(package_name)
    if "error" in stats:
        raise HTTPException(status_code=404, detail=stats["error"])

    deps = get_dependency_tree(package_name, limit=20)
    rev_deps = get_reverse_dependencies(package_name, limit=20)

    return {
        **stats,
        "dependencies": deps,
        "reverse_dependencies": rev_deps,
    }


@app.get("/api/compare")
async def compare(packages: str):
    pkg_list = [p.strip() for p in packages.split(",") if p.strip()]
    if len(pkg_list) < 2:
        raise HTTPException(status_code=400, detail="Provide at least 2 package names separated by commas")
    result = await compare_packages_intel(pkg_list)
    return result


@app.get("/api/health/{package_name}")
async def health_check(package_name: str):
    stats = await get_package_stats(package_name)
    if "error" in stats:
        raise HTTPException(status_code=404, detail=stats["error"])

    score = stats.get("reposcout_score", 0)
    risks = []

    if stats.get("days_since_last_release", 9999) > 365:
        risks.append("No release in over a year")
    if stats.get("days_since_last_release", 9999) > 730:
        risks.append("No release in over 2 years — possibly abandoned")
    if stats.get("dependents_count", 0) < 10:
        risks.append("Very low adoption (< 10 dependents)")
    if stats.get("stars", 0) < 50:
        risks.append("Low community engagement (< 50 stars)")
    if stats.get("total_versions", 0) < 3:
        risks.append("Very few releases — may be immature")

    return {
        **stats,
        "risks": risks,
        "risk_level": "high" if score < 40 else "moderate" if score < 70 else "low",
    }


@app.get("/api/search/quick")
async def quick_search(q: str, limit: int = 10):
    if not q.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    results = search_packages(q, limit=limit)
    return results


@app.get("/api/dependents/{package_name}")
async def dependents(package_name: str):
    count = get_dependents_count(package_name)
    rev_deps = get_reverse_dependencies(package_name, limit=50)
    return {
        "package_name": package_name,
        "dependents_count": count,
        "top_dependents": rev_deps,
    }


@app.get("/api/downloads")
async def downloads(packages: str):
    pkg_list = [p.strip() for p in packages.split(",") if p.strip()][:10]
    if not pkg_list:
        raise HTTPException(status_code=400, detail="Provide at least 1 package name")
    return get_download_history(pkg_list)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
