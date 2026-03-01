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
    client = get_client()

    # Safety: block unsafe content via Mistral Moderation
    rejection = moderate_query(user_query)
    if rejection:
        return {"analysis": rejection, "tool_calls": [], "iterations": 0, "mode": "rejected", "packages": [], "search": None}

    # Auto-detect mode if not explicitly set
    if mode == "auto":
        mode = classify_query(user_query)

    # Off-topic: classifier said reject
    if mode == "reject":
        return {"analysis": _REJECT_MSG, "tool_calls": [], "iterations": 0, "mode": "rejected", "packages": [], "search": None}

    mode_context = ""
    is_growth_query = bool(_GROWTH_QUERY_RE.search(user_query))
    if mode == "explore":
        if is_growth_query:
            mode_context = (
                "\nThe user is asking about FAST-GROWING or TRENDING packages. "
                "After using search_packages, look at the growth_pct field in results. "
                "You MUST call get_package_stats on the top 5 packages with the HIGHEST growth_pct values. "
                "Do NOT pick packages based on general popularity or fame — pick by growth rate. "
                "In your analysis, lead with the growth numbers and explain what's driving adoption."
            )
        else:
            mode_context = "\nThe user is exploring packages. After using search_packages, you MUST also call get_package_stats on the top 5 most relevant/popular packages to get detailed stats. Do not skip this step."
    elif mode == "compare":
        mode_context = "\nThe user wants to compare packages. Use the compare_packages tool and provide a detailed side-by-side analysis."

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT + mode_context},
        {"role": "user", "content": user_query},
    ]

    tool_calls_log = []
    packages_data = []  # structured package stats for frontend
    search_data = None  # search results for frontend

    response = client.chat.complete(
        model=MISTRAL_LARGE,
        messages=messages,
        tools=TOOLS,
        tool_choice="auto",
    )

    max_iterations = 8
    iteration = 0

    while response.choices[0].message.tool_calls and iteration < max_iterations:
        iteration += 1
        assistant_msg = response.choices[0].message
        messages.append(assistant_msg)

        for tool_call in assistant_msg.tool_calls:
            tool_name = tool_call.function.name
            tool_args = tool_call.function.arguments

            result = await execute_tool(tool_name, tool_args)
            result_parsed = json.loads(result) if isinstance(result, str) else result

            tool_calls_log.append({
                "tool": tool_name,
                "args": json.loads(tool_args) if isinstance(tool_args, str) else tool_args,
                "result_preview": result[:500] if len(result) > 500 else result,
            })

            # Collect structured data for frontend
            if tool_name == "search_packages":
                search_data = result_parsed
            elif tool_name == "get_package_stats" and "error" not in result_parsed:
                packages_data.append(result_parsed)
            elif tool_name == "compare_packages" and "packages" in result_parsed:
                packages_data.extend(result_parsed["packages"])

            messages.append({
                "role": "tool",
                "name": tool_name,
                "content": result,
                "tool_call_id": tool_call.id,
            })

        response = client.chat.complete(
            model=MISTRAL_LARGE,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
        )

    final_text = response.choices[0].message.content

    # For growth queries: override LLM's package picks with actual top growth packages
    if is_growth_query and search_data and not _SPECIFIC_DOMAIN_RE.search(user_query):
        growth_packages = []
        await _auto_fetch_top_growth(search_data, growth_packages, tool_calls_log, [])
        if growth_packages:
            packages_data = growth_packages

    return {
        "analysis": final_text,
        "tool_calls": tool_calls_log,
        "iterations": iteration,
        "mode": mode,
        "packages": packages_data,
        "search": search_data,
    }


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
    """Streaming version of run_agent.

    Uses async Mistral API calls so the event loop stays free to flush
    SSE events in real-time.  Yields:
      1. progress events  — live loading hints during the tool loop
      2. metadata dict    — cards render immediately
      3. token strings    — analysis text fills in progressively
      4. done signal
    """
    client = get_client()

    # Safety: block unsafe content via Mistral Moderation
    rejection = moderate_query(user_query)
    if rejection:
        yield {"type": "metadata", "tool_calls": [], "iterations": 0, "mode": "rejected", "packages": [], "search": None}
        yield {"type": "token", "content": rejection}
        yield {"type": "done"}
        return

    # --- Classify (async so we don't block the event loop) ---
    if mode == "auto":
        yield {"type": "progress", "step": "Classifying your query..."}
        try:
            cls_resp = await client.chat.complete_async(
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
                            "- 'who is the president' → reject\n\n"
                            "Respond with ONLY the category name, nothing else."
                        ),
                    },
                    {"role": "user", "content": user_query},
                ],
                max_tokens=10,
            )
            mode = cls_resp.choices[0].message.content.strip().lower()
            if mode not in ("explore", "compare", "reject"):
                mode = "explore"
        except Exception:
            mode = "explore"

    # Off-topic: classifier said reject
    if mode == "reject":
        yield {"type": "metadata", "tool_calls": [], "iterations": 0, "mode": "rejected", "packages": [], "search": None}
        yield {"type": "token", "content": _REJECT_MSG}
        yield {"type": "done"}
        return

    mode_context = ""
    is_growth_query = bool(_GROWTH_QUERY_RE.search(user_query))
    if mode == "explore":
        if is_growth_query:
            mode_context = (
                "\nThe user is asking about FAST-GROWING or TRENDING packages. "
                "After using search_packages, look at the growth_pct field in results. "
                "You MUST call get_package_stats on the top 5 packages with the HIGHEST growth_pct values. "
                "Do NOT pick packages based on general popularity or fame — pick by growth rate. "
                "In your analysis, lead with the growth numbers and explain what's driving adoption."
            )
        else:
            mode_context = "\nThe user is exploring packages. After using search_packages, you MUST also call get_package_stats on the top 5 most relevant/popular packages to get detailed stats. Do not skip this step."
    elif mode == "compare":
        mode_context = "\nThe user wants to compare packages. Use the compare_packages tool and provide a detailed side-by-side analysis."

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT + mode_context},
        {"role": "user", "content": user_query},
    ]

    tool_calls_log = []
    packages_data = []
    search_data = None

    yield {"type": "progress", "step": "Querying Mistral Large..."}

    # First LLM call (async — event loop stays free for SSE)
    response = await client.chat.complete_async(
        model=MISTRAL_LARGE,
        messages=messages,
        tools=TOOLS,
        tool_choice="auto",
    )

    max_iterations = 8
    iteration = 0

    while response.choices[0].message.tool_calls and iteration < max_iterations:
        iteration += 1
        assistant_msg = response.choices[0].message
        messages.append(assistant_msg)

        # Yield all progress hints first, then run tools in parallel
        tasks = []
        for tool_call in assistant_msg.tool_calls:
            tool_name = tool_call.function.name
            tool_args = tool_call.function.arguments
            args_parsed = json.loads(tool_args) if isinstance(tool_args, str) else tool_args

            display = TOOL_DISPLAY.get(tool_name, tool_name)
            detail = args_parsed.get("package_name") or args_parsed.get("query") or ""
            step_text = f"{display} {detail}".strip() if detail else display
            yield {"type": "progress", "step": step_text}

            tasks.append((tool_call, tool_name, args_parsed))

        # Run all tool calls concurrently
        results = await asyncio.gather(*[
            execute_tool(tc.function.name, tc.function.arguments)
            for tc, _, _ in tasks
        ])

        for (tool_call, tool_name, args_parsed), result in zip(tasks, results):
            result_parsed = json.loads(result) if isinstance(result, str) else result

            tool_calls_log.append({
                "tool": tool_name,
                "args": args_parsed,
                "result_preview": result[:500] if len(result) > 500 else result,
            })

            if tool_name == "search_packages":
                search_data = result_parsed
            elif tool_name == "get_package_stats" and "error" not in result_parsed:
                packages_data.append(result_parsed)
            elif tool_name == "compare_packages" and "packages" in result_parsed:
                packages_data.extend(result_parsed["packages"])

            messages.append({
                "role": "tool",
                "name": tool_name,
                "content": result,
                "tool_call_id": tool_call.id,
            })

        yield {"type": "progress", "step": "Synthesizing results..."}

        response = await client.chat.complete_async(
            model=MISTRAL_LARGE,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
        )

    # For growth queries: override LLM's package picks with actual top growth packages
    if is_growth_query and search_data and not _SPECIFIC_DOMAIN_RE.search(user_query):
        growth_packages = []
        await _auto_fetch_top_growth(search_data, growth_packages, tool_calls_log, [])
        if growth_packages:
            packages_data = growth_packages

    # --- Phase 1: yield metadata — cards render NOW ---
    yield {
        "type": "metadata",
        "tool_calls": tool_calls_log,
        "iterations": iteration,
        "mode": mode,
        "packages": packages_data,
        "search": search_data,
    }

    # --- Phase 2: fetch downloads in background while we chunk text ---
    pkg_names = [p.get("name", "") for p in packages_data if p.get("name")][:5]
    download_task = (
        asyncio.create_task(asyncio.to_thread(get_download_history, pkg_names))
        if pkg_names else None
    )

    # Yield the analysis text the tool loop already generated
    final_text = response.choices[0].message.content or ""
    chunk_size = 24
    for i in range(0, len(final_text), chunk_size):
        yield {"type": "token", "content": final_text[i : i + chunk_size]}
        await asyncio.sleep(0)  # yield control so SSE flushes each chunk

    # Yield download data (should be ready by now — ran in parallel with text)
    if download_task:
        try:
            download_data = await download_task
            if download_data:
                yield {"type": "downloads", "data": download_data}
        except Exception:
            pass

    yield {"type": "done"}
