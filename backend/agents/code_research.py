import json
from mistralai import Mistral
from backend.config import MISTRAL_API_KEY, DEVSTRAL
from backend.utils.github_fetcher import fetch_key_files, fetch_source_file, parse_repo_url
from backend.utils.duckdb_client import get_package

_client: Mistral | None = None


def get_client() -> Mistral:
    global _client
    if _client is None:
        _client = Mistral(api_key=MISTRAL_API_KEY)
    return _client


def analyze_code_with_devstral(code: str, question: str) -> dict:
    client = get_client()
    try:
        response = client.chat.complete(
            model=DEVSTRAL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a code analysis expert. Analyze the provided code and answer the question. "
                        "Be specific about implementation patterns, design decisions, and tradeoffs. "
                        "Respond with JSON containing: pattern_name (string), description (string), "
                        "key_features (list of strings), tradeoffs (list of strings), "
                        "usage_example (code string showing how to use it)"
                    ),
                },
                {
                    "role": "user",
                    "content": f"Code:\n```python\n{code[:8000]}\n```\n\nQuestion: {question}",
                },
            ],
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        return {
            "pattern_name": "Analysis unavailable",
            "description": f"Could not analyze code: {str(e)}",
            "key_features": [],
            "tradeoffs": [],
            "usage_example": "",
        }


async def fetch_and_analyze_code(package_name: str, question: str = "Describe the main implementation pattern") -> dict:
    # Get repo URL from DuckDB
    pkg = get_package(package_name)
    if not pkg:
        return {"error": f"Package '{package_name}' not found in database"}

    repo_url = pkg.get("Repository_URL", "")
    info = parse_repo_url(repo_url)
    if not info:
        return {"error": f"No GitHub repository found for '{package_name}'"}

    owner, repo = info

    # Fetch key files
    files = await fetch_key_files(owner, repo)
    if not files:
        return {"error": f"Could not fetch files from {owner}/{repo}"}

    # Pick the most relevant file for analysis
    code_to_analyze = ""
    source_file = ""
    if "README.md" in files:
        code_to_analyze = files["README.md"]
        source_file = "README.md"

    # Try to find main source files
    for branch in ["main", "master"]:
        # Common patterns for main module files
        for filepath in [
            f"{package_name}/__init__.py",
            f"{package_name}/core.py",
            f"{package_name}/main.py",
            f"{package_name.replace('-', '_')}/__init__.py",
            f"{package_name.replace('-', '_')}/core.py",
            f"src/{package_name}/__init__.py",
        ]:
            content = await fetch_source_file(repo_url, filepath)
            if content and len(content) > 50:
                code_to_analyze = content
                source_file = filepath
                break
        if source_file and source_file != "README.md":
            break

    if not code_to_analyze:
        return {"error": f"Could not find analyzable source code for '{package_name}'"}

    # Analyze with Devstral
    analysis = analyze_code_with_devstral(code_to_analyze, question)
    analysis["source_file"] = source_file
    analysis["repo_url"] = repo_url
    analysis["code_snippet"] = code_to_analyze[:3000]

    return analysis
