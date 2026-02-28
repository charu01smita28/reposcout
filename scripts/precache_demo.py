"""
Pre-cache demo queries so they return instantly during the demo.

Usage:
    python -m scripts.precache_demo
"""

import asyncio
import json
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CACHE_DIR = BASE_DIR / "data" / "demo_cache"

import sys
sys.path.insert(0, str(BASE_DIR))

from backend.agents.orchestrator import run_agent
from backend.agents.package_intel import get_package_stats, compare_packages_intel

DEMO_QUERIES = [
    {
        "query": "How do Python projects handle rate limiting?",
        "mode": "explore",
    },
    {
        "query": "Compare FastAPI vs Django vs Flask",
        "mode": "compare",
    },
    {
        "query": "Is python-jose safe to depend on?",
        "mode": "health_check",
    },
    {
        "query": "What's the fastest growing Python ORM?",
        "mode": "explore",
    },
]

# Pre-fetch PyPI metadata for packages likely to appear in demo
DEMO_PACKAGES = [
    "fastapi", "django", "flask", "requests", "sqlalchemy",
    "ratelimit", "slowapi", "flask-limiter",
    "python-jose", "pyjwt", "authlib",
    "tortoise-orm", "peewee", "pony", "sqlmodel",
    "numpy", "pandas", "httpx", "uvicorn", "pydantic",
]


async def precache_packages():
    print("[...] Pre-caching PyPI metadata for demo packages...")
    for pkg_name in DEMO_PACKAGES:
        try:
            stats = await get_package_stats(pkg_name)
            print(f"  [OK] {pkg_name}: score={stats.get('reposcout_score', '?')}")
        except Exception as e:
            print(f"  [ERR] {pkg_name}: {e}")


async def precache_queries():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    print("\n[...] Pre-caching demo queries...")
    for demo in DEMO_QUERIES:
        query = demo["query"]
        mode = demo["mode"]
        cache_key = query.lower().replace(" ", "_").replace("?", "")[:60]
        cache_path = CACHE_DIR / f"{cache_key}.json"

        print(f"\n  Query: \"{query}\" (mode={mode})")
        t0 = time.time()

        try:
            result = await run_agent(query, mode=mode)
            elapsed = time.time() - t0

            cache_data = {
                "query": query,
                "mode": mode,
                "result": result,
                "cached_at": time.time(),
                "generation_time_seconds": elapsed,
            }
            cache_path.write_text(json.dumps(cache_data, indent=2, default=str))
            print(f"  [OK] Cached in {elapsed:.1f}s → {cache_path.name}")
        except Exception as e:
            print(f"  [ERR] Failed: {e}")


async def main():
    await precache_packages()
    await precache_queries()
    print("\n[DONE] Demo cache ready!")
    print(f"  Cache dir: {CACHE_DIR}")


if __name__ == "__main__":
    asyncio.run(main())
