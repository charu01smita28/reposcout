import json
from mistralai import Mistral
from backend.config import MISTRAL_API_KEY, MISTRAL_LARGE, MINISTRAL
from backend.agents.package_intel import (
    search_packages,
    get_package_stats,
    get_dependents,
    compare_packages_intel,
)
from backend.agents.code_research import fetch_and_analyze_code
from backend.agents.synthesis import synthesize_response

_client: Mistral | None = None

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_packages",
            "description": "Semantic search across 400K+ Python packages to find packages related to a topic or functionality. Returns package names, descriptions, stars, and relevance scores.",
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
            "description": "Get the number of packages that depend on a given package from the 235M dependency relationship database.",
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

SYSTEM_PROMPT = """You are RepoScout, an open source intelligence engine with access to a database of 2.6M+ packages and 235M dependency relationships from the PyPI ecosystem.

You help developers make data-driven decisions about open source packages. You have real data — not opinions.

CRITICAL FORMAT RULE — NEVER include tables of raw stats (stars, dependents, health scores, release dates, etc.) in your response. The UI already shows all package data in an interactive comparison card. Repeating it wastes space. Instead, go straight to ANALYSIS and RECOMMENDATIONS. You may reference specific numbers inline (e.g. "Django leads with 10,816 dependents") but NEVER format them as a table.

Your capabilities via tools:
- search_packages: Semantic search across 400K+ Python package descriptions
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
7. NEVER wrap package names in backticks. Write package names as plain text (e.g. "pypdf" not "`pypdf`"). Backticks should only be used for actual code snippets like pip install commands."""


def get_client() -> Mistral:
    global _client
    if _client is None:
        _client = Mistral(api_key=MISTRAL_API_KEY)
    return _client


TOOL_EXECUTORS = {
    "search_packages": lambda args: search_packages(args["query"]),
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
                        "head-to-head (e.g. 'FastAPI vs Django', 'compare requests and httpx')\n\n"
                        "Examples:\n"
                        "- 'best Python ORMs' → explore\n"
                        "- 'How do Python projects handle rate limiting?' → explore\n"
                        "- 'best libraries for rate limiting' → explore\n"
                        "- 'is celery well maintained?' → explore\n"
                        "- 'should I use SQLAlchemy?' → explore\n"
                        "- 'what are the best testing frameworks' → explore\n"
                        "- 'FastAPI vs Django vs Flask' → compare\n"
                        "- 'compare requests and httpx' → compare\n\n"
                        "Respond with ONLY the category name, nothing else."
                    ),
                },
                {"role": "user", "content": query},
            ],
            max_tokens=10,
        )
        mode = response.choices[0].message.content.strip().lower()
        if mode in ("explore", "compare"):
            return mode
    except Exception:
        pass
    return "explore"


async def run_agent(user_query: str, mode: str = "auto") -> dict:
    client = get_client()

    # Auto-detect mode if not explicitly set
    if mode == "auto":
        mode = classify_query(user_query)

    mode_context = ""
    if mode == "explore":
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

    return {
        "analysis": final_text,
        "tool_calls": tool_calls_log,
        "iterations": iteration,
        "mode": mode,
        "packages": packages_data,
        "search": search_data,
    }
