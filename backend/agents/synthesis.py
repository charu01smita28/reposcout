import json
from mistralai import Mistral
from backend.config import MISTRAL_API_KEY, MISTRAL_LARGE

_client: Mistral | None = None


def get_client() -> Mistral:
    global _client
    if _client is None:
        _client = Mistral(api_key=MISTRAL_API_KEY)
    return _client


def synthesize_response(query: str, data: dict, mode: str = "explore") -> dict:
    client = get_client()

    if mode == "explore":
        prompt = _build_explore_prompt(query, data)
    elif mode == "compare":
        prompt = _build_compare_prompt(query, data)
    else:
        prompt = _build_explore_prompt(query, data)

    try:
        response = client.chat.complete(
            model=MISTRAL_LARGE,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are RepoScout's synthesis engine. You receive raw data about open source packages "
                        "and produce clear, data-driven analysis. Always cite specific numbers. "
                        "Respond with JSON containing: summary (string), recommendation (string), "
                        "key_findings (list of strings), follow_up_suggestions (list of 3 strings — "
                        "each a natural language question the user might want to ask next)"
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        return {
            "summary": f"Analysis could not be completed: {str(e)}",
            "recommendation": "",
            "key_findings": [],
            "follow_up_suggestions": [],
        }


def _build_explore_prompt(query: str, data: dict) -> str:
    return f"""User query: "{query}"

Here is the raw data gathered from our database of 2.6M packages and 235M dependency relationships:

{json.dumps(data, indent=2, default=str)[:6000]}

Synthesize this into a clear analysis. Include:
1. How many packages relate to this topic
2. Which is most popular by adoption (dependents count)
3. Which is growing fastest or has the best health score
4. A clear recommendation with reasoning
5. 3 follow-up questions the user might want to explore"""


def _build_compare_prompt(query: str, data: dict) -> str:
    return f"""User query: "{query}"

Here is the comparison data from our database:

{json.dumps(data, indent=2, default=str)[:6000]}

Synthesize a head-to-head comparison. Include:
1. Winner in each category (adoption, maintenance, community, health score)
2. Overall recommendation based on the data
3. When you'd choose each package
4. 3 follow-up questions"""


def _build_health_prompt(query: str, data: dict) -> str:
    return f"""User query: "{query}"

Here is the health data from our database:

{json.dumps(data, indent=2, default=str)[:6000]}

Synthesize a health assessment. Include:
1. Overall health verdict (healthy / moderate risk / high risk)
2. Specific risk factors found
3. Whether alternatives exist and which are healthier
4. Clear recommendation on whether to use this package
5. 3 follow-up questions"""
