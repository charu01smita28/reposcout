import httpx
from urllib.parse import urlparse
from backend.config import GITHUB_TOKEN

_http_client: httpx.AsyncClient | None = None


async def get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None:
        headers = {}
        if GITHUB_TOKEN:
            headers["Authorization"] = f"token {GITHUB_TOKEN}"
        _http_client = httpx.AsyncClient(headers=headers, timeout=15.0)
    return _http_client


def parse_repo_url(repo_url: str) -> tuple[str, str] | None:
    if not repo_url:
        return None
    parsed = urlparse(repo_url.rstrip("/"))
    parts = parsed.path.strip("/").split("/")
    if len(parts) >= 2:
        return parts[0], parts[1]
    return None


async def fetch_raw_file(owner: str, repo: str, branch: str, filepath: str) -> str | None:
    client = await get_http_client()
    url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{filepath}"
    try:
        response = await client.get(url)
        if response.status_code == 200:
            return response.text
    except httpx.RequestError:
        pass
    return None


async def fetch_readme(owner: str, repo: str) -> str | None:
    for name in ["README.md", "readme.md", "README.rst", "README"]:
        for branch in ["main", "master"]:
            content = await fetch_raw_file(owner, repo, branch, name)
            if content:
                return content
    return None


async def fetch_key_files(owner: str, repo: str) -> dict[str, str]:
    files = {}
    readme = await fetch_readme(owner, repo)
    if readme:
        files["README.md"] = readme

    for branch in ["main", "master"]:
        for setup_file in ["pyproject.toml", "setup.py", "setup.cfg"]:
            content = await fetch_raw_file(owner, repo, branch, setup_file)
            if content:
                files[setup_file] = content
                break
        if any(f in files for f in ["pyproject.toml", "setup.py", "setup.cfg"]):
            break

    return files


async def fetch_source_file(repo_url: str, filepath: str) -> str | None:
    info = parse_repo_url(repo_url)
    if not info:
        return None
    owner, repo = info
    for branch in ["main", "master"]:
        content = await fetch_raw_file(owner, repo, branch, filepath)
        if content:
            return content
    return None
