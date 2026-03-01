import asyncio
import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(name)s | %(message)s")

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from backend.models import SearchRequest
from backend.agents.orchestrator import run_agent, run_agent_stream
from backend.agents.package_intel import get_package_stats, compare_packages_intel, search_packages
from backend.utils.duckdb_client import get_dataset_stats, get_dependents_count, get_dependency_tree, get_reverse_dependencies, get_download_history
from backend.utils.scoring import get_score_label, get_score_color

# --- SSE Stream Cache ---
STREAM_CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "stream_cache"
STREAM_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Replay delays per event type (seconds) — feels natural, not instant
_REPLAY_DELAYS = {
    "progress": 1.2,
    "metadata": 0.1,
    "token": 0.0,    # tokens flush via sleep(0)
    "downloads": 0.0,
    "done": 0.0,
}


def _cache_key(query: str, mode: str) -> str:
    return query.strip().lower().replace(" ", "_")[:80] + f"__{mode}"


_STOP_WORDS = {"a", "an", "the", "is", "are", "for", "in", "of", "to", "and", "or", "what", "how", "do", "does", "vs", "best", "top"}


def _query_words(query: str) -> set[str]:
    return {w for w in query.strip().lower().split() if w not in _STOP_WORDS and len(w) > 1}


def _read_cache(key: str) -> list[dict] | None:
    # Exact match first
    path = STREAM_CACHE_DIR / f"{key}.json"
    if path.exists():
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            pass

    # Fuzzy match: 4+ significant words overlap → cache hit
    query_part, _, mode_part = key.rpartition("__")
    if not query_part:
        return None
    input_words = _query_words(query_part.replace("_", " "))
    if len(input_words) < 3:
        return None

    best_match = None
    best_overlap = 0
    for cached_file in STREAM_CACHE_DIR.glob(f"*__{mode_part}.json"):
        cached_query = cached_file.stem.rpartition("__")[0].replace("_", " ")
        cached_words = _query_words(cached_query)
        overlap = len(input_words & cached_words)
        if overlap > best_overlap:
            best_overlap = overlap
            best_match = cached_file

    if best_overlap >= 4 and best_match:
        try:
            return json.loads(best_match.read_text())
        except (json.JSONDecodeError, OSError):
            pass

    return None


def _write_cache(key: str, events: list[dict]):
    path = STREAM_CACHE_DIR / f"{key}.json"
    path.write_text(json.dumps(events, default=str))

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


@app.post("/api/search/stream")
async def search_stream(req: SearchRequest):
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    key = _cache_key(req.query, req.mode)
    cached = _read_cache(key)

    if cached:
        # Replay cached events with realistic delays
        async def replay_generator():
            for event in cached:
                delay = _REPLAY_DELAYS.get(event.get("type", ""), 0)
                if delay > 0:
                    await asyncio.sleep(delay)
                yield f"data: {json.dumps(event, default=str)}\n\n"
                if event.get("type") == "token":
                    await asyncio.sleep(0)  # flush each token chunk

        return StreamingResponse(
            replay_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    # Live pipeline — collect events and cache them
    async def event_generator():
        events: list[dict] = []
        async for chunk in run_agent_stream(req.query, mode=req.mode):
            events.append(chunk)
            yield f"data: {json.dumps(chunk, default=str)}\n\n"
        # Save to cache after stream completes
        _write_cache(key, events)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


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
