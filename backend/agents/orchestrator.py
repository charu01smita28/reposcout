import asyncio
import json
import re
from mistralai import Mistral
from backend.config import MISTRAL_API_KEY, MISTRAL_LARGE, MINISTRAL
from backend.utils.duckdb_client import get_download_history
from backend.agents.package_intel import (
    search_packages,
    get_package_stats,
    get_dependents,
    compare_packages_intel,
)
from backend.agents.code_research import fetch_and_analyze_code
from backend.agents.synthesis import synthesize_response

_GROWTH_QUERY_RE = re.compile(
    r"(grow|trend|rising|fastest|hottest|explod|surge|boom|emerging)",
    re.IGNORECASE,
)

# Domain-specific queries — growth override should NOT apply
_SPECIFIC_DOMAIN_RE = re.compile(
    r"\b(orm|database|web.?scrap|test|auth|http|api|async|queue|cache|log|email|csv|excel|pdf|image|video|cli|gui)\b",
    re.IGNORECASE,
)

_client: Mistral | None = None

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_packages",
            "description": "Semantic search across 85K+ Python packages with 2M+ dependency signals to find packages related to a topic or functionality. Returns package names, descriptions, stars, and relevance scores.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The topic or functionality to search for (e.g. 'rate limiting', 'ORM', 'authentication')",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_package_stats",
            "description": "Get detailed statistics for a specific PyPI package: dependents count, stars, forks, health score, version history, and maintenance status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "package_name": {
                        "type": "string",
                        "description": "The exact PyPI package name (e.g. 'fastapi', 'django')",
                    }
                },
                "required": ["package_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_dependents_count",
            "description": "Get the number of packages that depend on a given package from the 2M+ dependency signals database.",
            "parameters": {
                "type": "object",
                "properties": {
                    "package_name": {
                        "type": "string",
                        "description": "The exact PyPI package name",
                    }
                },
                "required": ["package_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_packages",
            "description": "Compare two or more PyPI packages side by side with adoption data, health scores, stars, and maintenance metrics.",
            "parameters": {
                "type": "object",
                "properties": {
                    "package_names": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of PyPI package names to compare",
                    }
                },
                "required": ["package_names"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_source_code",
            "description": "Fetch and analyze source code from a package's GitHub repository using Devstral AI code analysis.",
            "parameters": {
                "type": "object",
                "properties": {
                    "package_name": {
                        "type": "string",
                        "description": "The PyPI package name whose source code to fetch and analyze",
                    },
                    "question": {
                        "type": "string",
                        "description": "What to analyze about the code (e.g. 'How does rate limiting work?')",
                    },
                },
                "required": ["package_name"],
            },
        },
    },
]

SYSTEM_PROMPT = """You are RepoScout, an open source intelligence engine with access to a database of 85K+ packages and 2M+ dependency signals from the PyPI ecosystem.

You help developers make data-driven decisions about open source packages. You have real data — not opinions.

CRITICAL FORMAT RULE — NEVER include tables of raw stats (stars, dependents, health scores, release dates, etc.) in your response. The UI already shows all package data in an interactive comparison card. Repeating it wastes space. Instead, go straight to ANALYSIS and RECOMMENDATIONS. You may reference specific numbers inline (e.g. "Django leads with 10,816 dependents") but NEVER format them as a table.

Your capabilities via tools:
- search_packages: Semantic search across 85K+ Python packages with 2M+ dependency signals
- get_package_stats: Detailed stats for any package (dependents, stars, health score)
- get_dependents_count: Exact number of packages depending on a given package
- compare_packages: Side-by-side comparison of multiple packages
- fetch_source_code: Fetch and analyze actual source code from GitHub

IMPORTANT RULES:
1. Always use tools to get real data before answering. Never guess or use training data for package stats.
2. Cite specific numbers inline but NEVER as a data summary table — the UI handles that.
3. When comparing, use actual adoption data (dependents), not just stars.
4. If a package isn't found in the database, say so honestly.
5. Structure your response with: Key Insights → Use Cases → Recommendations.
6. When recommending a package, explain WHY with data points.
7. NEVER use backticks (`) around package names or library names. Write them as plain text: "scikit-learn" not "`scikit-learn`", "torch" not "`torch`". The ONLY place backticks are allowed is for actual shell commands like `pip install torch`. This rule is absolute — violating it breaks the UI rendering."""


def get_client() -> Mistral:
    global _client
    if _client is None:
        _client = Mistral(api_key=MISTRAL_API_KEY)
    return _client


TOOL_EXECUTORS = {
    "search_packages": lambda args: search_packages(args["query"], limit=30),
    "get_package_stats": lambda args: get_package_stats(args["package_name"]),
    "get_dependents_count": lambda args: get_dependents(args["package_name"]),
    "compare_packages": lambda args: compare_packages_intel(args["package_names"]),
    "fetch_source_code": lambda args: fetch_and_analyze_code(
        args["package_name"], args.get("question", "Describe the main implementation pattern")
    ),
}


async def execute_tool(name: str, arguments: str) -> str:
    args = json.loads(arguments) if isinstance(arguments, str) else arguments
    executor = TOOL_EXECUTORS.get(name)
    if not executor:
        return json.dumps({"error": f"Unknown tool: {name}"})

    import asyncio
    result = executor(args)
    if asyncio.iscoroutine(result):
        result = await result
    return json.dumps(result, default=str)


_REJECT_MSG = (
    "I'm RepoScout — I help with Python package discovery, comparison, and health analysis. "
    "Try asking something like:\n\n"
    "- *What are the best Python libraries for web scraping?*\n"
    "- *Compare FastAPI vs Django vs Flask*\n"
    "- *Is celery well maintained?*\n"
    "- *What are the fastest growing AI libraries?*"
)


def moderate_query(query: str) -> str | None:
    """Use Mistral Moderation to block unsafe content. Returns rejection message or None."""
    client = get_client()
    try:
        moderation = client.classifiers.moderate_chat(
            model="mistral-moderation-latest",
            messages=[{"role": "user", "content": query}],
        )
        categories = moderation.results[0].categories
        # Check all category flags
        for cat_name in vars(categories):
            if not cat_name.startswith("_") and getattr(categories, cat_name, False):
                return _REJECT_MSG
    except Exception:
        pass  # Don't block on moderation API failures
    return None


def classify_query(query: str) -> str:
    """Use Ministral 8B to classify query intent. Fast, cheap, accurate."""
    client = get_client()
    try:
        response = client.chat.complete(
            model=MINISTRAL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a query classifier for a Python package intelligence tool. "
                        "Classify the user's query into exactly one category.\n\n"
                        "Categories:\n"
                        "- explore: ANY query about discovering, evaluating, or learning about packages. "
                        "This includes searching by topic, asking about a concept, asking if a package is good, "
                        "finding alternatives, or anything that is NOT an explicit side-by-side comparison. "
                        "This is the default and most common category.\n"
                        "- compare: ONLY when the user explicitly asks to compare two or more NAMED packages "
                        "head-to-head (e.g. 'FastAPI vs Django', 'compare requests and httpx')\n"
                        "- reject: The query has NOTHING to do with Python packages, libraries, open source, "
                        "software development, or programming. Examples: weather, sports, cooking, jokes, "
                        "personal questions, math homework, general knowledge trivia.\n\n"
                        "Examples:\n"
                        "- 'best Python ORMs' → explore\n"
                        "- 'How do Python projects handle rate limiting?' → explore\n"
                        "- 'best libraries for rate limiting' → explore\n"
                        "- 'is celery well maintained?' → explore\n"
                        "- 'should I use SQLAlchemy?' → explore\n"
                        "- 'what are the best testing frameworks' → explore\n"
                        "- 'FastAPI vs Django vs Flask' → compare\n"
                        "- 'compare requests and httpx' → compare\n"
                        "- 'what is the weather today' → reject\n"
                        "- 'tell me a joke' → reject\n"
                        "- 'who is the president' → reject\n"
                        "- 'write me a poem' → reject\n"
                        "- 'how to cook pasta' → reject\n"
                        "- 'what is 2+2' → reject\n\n"
                        "Respond with ONLY the category name, nothing else."
                    ),
                },
                {"role": "user", "content": query},
            ],
            max_tokens=10,
        )
        mode = response.choices[0].message.content.strip().lower()
        if mode in ("explore", "compare", "reject"):
            return mode
    except Exception:
        pass
    return "explore"


async def run_agent(user_query: str, mode: str = "auto") -> dict:
    """Non-streaming agent loop.

    Pipeline:
    1. Moderate query via Mistral Moderation API
    2. Classify intent via Ministral 8B (explore/compare/reject)
    3. Build mode-aware system prompt (growth-aware for trending queries)
    4. Multi-iteration tool loop with Mistral Large (up to 8 iterations)
    5. Collect structured package data + search results for frontend cards
    6. Growth override: re-rank by growth_pct * ln(deps) for trending queries
    7. Returns: { analysis, tool_calls, iterations, mode, packages[], search }
    """
    # --- Implementation removed for public repository ---
    raise NotImplementedError


async def _auto_fetch_top_growth(search_result: dict, packages_data: list, tool_calls_log: list, messages: list):
    """For growth queries: auto-fetch stats for top packages by growth with real adoption.
    Filters for 200+ deps and 500+ stars to exclude noise, then picks top 7 by growth_pct."""
    pkgs = search_result.get("packages", [])
    # Filter for real adoption, then sort by growth
    quality = [
        p for p in pkgs
        if p.get("dependents_count", p.get("dependent_count", 0)) >= 200
        and p.get("stars", 0) >= 500
    ]
    quality.sort(key=lambda p: p.get("growth_pct", 0), reverse=True)
    top = quality[:7]

    # Fallback: if quality filter is too strict, use top 5 by growth_pct * ln(deps)
    if len(top) < 3:
        import math
        by_growth = sorted(pkgs, key=lambda p: p.get("growth_pct", 0) * math.log(max(p.get("dependents_count", p.get("dependent_count", 0)), 1) + 1), reverse=True)
        top = by_growth[:5]

    already_fetched = {p.get("name", "").lower() for p in packages_data}
    fetched_summaries = []

    for pkg in top:
        name = pkg.get("name", "")
        if not name or name.lower() in already_fetched:
            continue
        already_fetched.add(name.lower())
        result_str = await execute_tool("get_package_stats", json.dumps({"package_name": name}))
        result_parsed = json.loads(result_str)
        if "error" not in result_parsed:
            packages_data.append(result_parsed)
            tool_calls_log.append({
                "tool": "get_package_stats",
                "args": {"package_name": name},
                "result_preview": result_str[:500],
            })
            fetched_summaries.append(f"- {name}: {result_str[:500]}")

    # Add as a single user message so Mistral Large sees the data (must end on user role)
    if fetched_summaries:
        messages.append({
            "role": "user",
            "content": "Here are detailed stats for the top growth packages:\n" + "\n".join(fetched_summaries),
        })


TOOL_DISPLAY = {
    "search_packages": "Searching 80K+ packages",
    "get_package_stats": "Fetching stats for",
    "get_dependents_count": "Counting dependents for",
    "compare_packages": "Comparing packages",
    "fetch_source_code": "Analyzing source code for",
}


async def run_agent_stream(user_query: str, mode: str = "auto"):
    """Streaming version of run_agent with SSE delivery.

    Uses async Mistral API calls so the event loop stays free to flush
    SSE events in real-time. Yields:
      1. progress events  — live loading hints during the tool loop
      2. metadata dict    — cards render immediately (metadata-first pattern)
      3. token strings    — analysis text fills in progressively (24-char chunks)
      4. download data    — fetched concurrently via asyncio.create_task()
      5. done signal

    Key design decisions:
    - Async classification via Ministral 8B (non-blocking)
    - Parallel tool execution via asyncio.gather() within each iteration
    - Metadata yielded before text so frontend renders cards instantly
    - Download history fetched concurrently with text streaming
    - asyncio.sleep(0) after each chunk for smooth SSE delivery
    """
    # --- Implementation removed for public repository ---
    raise NotImplementedError
