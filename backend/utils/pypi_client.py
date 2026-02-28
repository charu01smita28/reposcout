import json
import httpx
from pathlib import Path
from datetime import datetime
from backend.config import PYPI_CACHE_DIR

_http_client: httpx.AsyncClient | None = None

PYPI_CACHE_DIR.mkdir(parents=True, exist_ok=True)


async def get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(timeout=10.0)
    return _http_client


def _cache_path(package_name: str) -> Path:
    return PYPI_CACHE_DIR / f"{package_name.lower()}.json"


def _read_cache(package_name: str) -> dict | None:
    path = _cache_path(package_name)
    if path.exists():
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return None


def _write_cache(package_name: str, data: dict):
    path = _cache_path(package_name)
    path.write_text(json.dumps(data))


def _get_latest_release_date(releases: dict) -> str | None:
    latest_date = None
    for version, files in releases.items():
        for f in files:
            upload_time = f.get("upload_time")
            if upload_time:
                if latest_date is None or upload_time > latest_date:
                    latest_date = upload_time
    return latest_date


async def get_pypi_metadata(package_name: str, use_cache: bool = True) -> dict | None:
    if use_cache:
        cached = _read_cache(package_name)
        if cached:
            return cached

    client = await get_http_client()
    url = f"https://pypi.org/pypi/{package_name}/json"
    try:
        response = await client.get(url)
        if response.status_code != 200:
            return None

        data = response.json()
        info = data["info"]
        releases = data.get("releases", {})

        result = {
            "name": info.get("name"),
            "version": info.get("version"),
            "summary": info.get("summary"),
            "author": info.get("author"),
            "license": info.get("license"),
            "home_page": info.get("home_page"),
            "project_url": info.get("project_url"),
            "requires_dist": info.get("requires_dist"),
            "total_versions": len(releases),
            "latest_release_date": _get_latest_release_date(releases),
        }

        _write_cache(package_name, result)
        return result
    except (httpx.RequestError, json.JSONDecodeError):
        return None


def days_since_release(release_date_str: str | None) -> int:
    if not release_date_str:
        return 9999
    try:
        release_date = datetime.fromisoformat(release_date_str.replace("Z", "+00:00"))
        delta = datetime.now(release_date.tzinfo) - release_date
        return delta.days
    except (ValueError, TypeError):
        return 9999
