export const suggestedQueries = [
  {
    icon: "Search" as const,
    query: "How do Python projects handle rate limiting?",
    borderColor: "border-l-[#6366f1]",
  },
  {
    icon: "GitCompare" as const,
    query: "Compare FastAPI vs Django vs Flask",
    borderColor: "border-l-[#10b981]",
  },
  {
    icon: "Shield" as const,
    query: "Is python-jose safe to depend on?",
    borderColor: "border-l-[#f59e0b]",
  },
  {
    icon: "TrendingUp" as const,
    query: "What's the fastest growing Python ORM?",
    borderColor: "border-l-[#8b5cf6]",
  },
]

export const statCards = [
  { label: "Packages Found", value: 47, type: "number" as const },
  { label: "Total Dependents", value: 234500, type: "number" as const },
  {
    label: "Most Popular",
    value: "ratelimit",
    sub: "12,400 dependents",
    type: "text" as const,
  },
  {
    label: "Fastest Growing",
    value: "slowapi",
    sub: "312% YoY",
    type: "growth" as const,
  },
]

export interface PackageData {
  name: string
  dependents: number
  stars: number
  health: number
  lastRelease: string
  lastReleaseStatus: "green" | "amber" | "red"
  trend: number
  trendDirection: "up" | "down" | "neutral"
}

export const packageData: PackageData[] = [
  {
    name: "ratelimit",
    dependents: 12400,
    stars: 1850,
    health: 92,
    lastRelease: "2 weeks ago",
    lastReleaseStatus: "green",
    trend: 15,
    trendDirection: "up",
  },
  {
    name: "slowapi",
    dependents: 3200,
    stars: 2100,
    health: 95,
    lastRelease: "1 week ago",
    lastReleaseStatus: "green",
    trend: 312,
    trendDirection: "up",
  },
  {
    name: "flask-limiter",
    dependents: 2800,
    stars: 1200,
    health: 78,
    lastRelease: "3 months ago",
    lastReleaseStatus: "amber",
    trend: 2,
    trendDirection: "neutral",
  },
  {
    name: "django-ratelimit",
    dependents: 1100,
    stars: 890,
    health: 85,
    lastRelease: "1 month ago",
    lastReleaseStatus: "green",
    trend: 8,
    trendDirection: "up",
  },
  {
    name: "limits",
    dependents: 890,
    stars: 450,
    health: 65,
    lastRelease: "8 months ago",
    lastReleaseStatus: "amber",
    trend: 5,
    trendDirection: "down",
  },
]

export const barChartData = [
  { name: "ratelimit", dependents: 12400 },
  { name: "slowapi", dependents: 3200 },
  { name: "flask-limiter", dependents: 2800 },
  { name: "django-ratelimit", dependents: 1100 },
  { name: "limits", dependents: 890 },
]

export const lineChartData = [
  { month: "Mar", ratelimit: 9200, slowapi: 400, "flask-limiter": 2500 },
  { month: "Apr", ratelimit: 9500, slowapi: 580, "flask-limiter": 2520 },
  { month: "May", ratelimit: 9800, slowapi: 750, "flask-limiter": 2550 },
  { month: "Jun", ratelimit: 10100, slowapi: 980, "flask-limiter": 2580 },
  { month: "Jul", ratelimit: 10400, slowapi: 1200, "flask-limiter": 2600 },
  { month: "Aug", ratelimit: 10700, slowapi: 1500, "flask-limiter": 2620 },
  { month: "Sep", ratelimit: 11000, slowapi: 1850, "flask-limiter": 2650 },
  { month: "Oct", ratelimit: 11300, slowapi: 2100, "flask-limiter": 2680 },
  { month: "Nov", ratelimit: 11600, slowapi: 2400, "flask-limiter": 2700 },
  { month: "Dec", ratelimit: 11900, slowapi: 2650, "flask-limiter": 2740 },
  { month: "Jan", ratelimit: 12100, slowapi: 2900, "flask-limiter": 2770 },
  { month: "Feb", ratelimit: 12400, slowapi: 3200, "flask-limiter": 2800 },
]

export const dependencyTree = {
  name: "rate limiting",
  children: [
    {
      name: "ratelimit",
      dependents: 12400,
      health: 92,
      dependencies: ["redis", "setuptools"],
      usedBy: "5,200 projects",
    },
    {
      name: "slowapi",
      dependents: 3200,
      health: 95,
      dependencies: ["starlette", "limits", "redis"],
      usedBy: "1,800 projects",
    },
    {
      name: "flask-limiter",
      dependents: 2800,
      health: 78,
      dependencies: ["flask", "limits", "redis"],
      usedBy: "1,400 projects",
    },
    {
      name: "django-ratelimit",
      dependents: 1100,
      health: 85,
      dependencies: ["django", "redis"],
      usedBy: "340 projects",
    },
  ],
}

export const packageDeepDive = {
  name: "slowapi",
  version: "0.1.9",
  description:
    "A rate limiter for Starlette and FastAPI, adapted from flask-limiter with native async support.",
  health: 95,
  metrics: [
    {
      label: "Maintainers",
      value: "2 active",
      icon: "Users" as const,
      status: "green" as const,
    },
    {
      label: "Release Frequency",
      value: "Weekly",
      icon: "Calendar" as const,
      status: "green" as const,
    },
    {
      label: "Issue Response",
      value: "< 24hrs",
      icon: "MessageCircle" as const,
      status: "green" as const,
    },
    {
      label: "Dependencies",
      value: "3 direct",
      icon: "GitBranch" as const,
      status: "green" as const,
    },
  ],
  codeSnippet: `from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(
    RateLimitExceeded,
    _rate_limit_exceeded_handler
)

@app.get("/api/endpoint")
@limiter.limit("5/minute")
async def my_endpoint(request: Request):
    return {"message": "Hello, World!"}`,
  codeSource: "From slowapi/extension.py, line 45-62",
}

export const aiSynthesis = {
  summary:
    'Based on analysis of 47 Python rate limiting packages across 234,500 dependent projects:',
  recommendation:
    '**slowapi** is the recommended choice for new FastAPI projects due to 312% growth and native async support. For Django projects, **django-ratelimit** remains the standard with strong maintainer activity. If you need a framework-agnostic solution, **limits** provides the most flexible backend support (Redis, Memcached, MongoDB) but shows declining adoption.',
  dataSources: [
    "Libraries.io package registry (2.6M packages)",
    "GitHub API (stars, issues, commits)",
    "PyPI download statistics",
    "Dependency graph analysis (235M relationships)",
  ],
  followUps: [
    {
      text: "Tell me more about slowapi's implementation",
      borderColor: "border-l-[#6366f1]",
    },
    {
      text: "Compare the Redis-based approaches",
      borderColor: "border-l-[#10b981]",
    },
    {
      text: "What are the security considerations?",
      borderColor: "border-l-[#f59e0b]",
    },
  ],
}

export const loadingSteps = [
  "Searching 400K Python packages...",
  "Analyzing dependency graph...",
  "Fetching source code...",
  "Synthesizing results...",
]
