export const suggestedQueries: Record<string, { icon: string; query: string; borderColor: string }[]> = {
  auto: [
    { icon: "Search", query: "How do Python projects handle rate limiting?", borderColor: "border-l-[#6366f1]" },
    { icon: "GitCompare", query: "Compare FastAPI vs Django vs Flask", borderColor: "border-l-[#10b981]" },
    { icon: "TrendingUp", query: "What's the fastest growing Python ORM?", borderColor: "border-l-[#f59e0b]" },
    { icon: "Package", query: "Best Python libraries for web scraping", borderColor: "border-l-[#8b5cf6]" },
  ],
  explore: [
    { icon: "Search", query: "Best Python libraries for web scraping", borderColor: "border-l-[#6366f1]" },
    { icon: "Search", query: "Top Python libraries for data validation", borderColor: "border-l-[#10b981]" },
    { icon: "Search", query: "Best Python libraries for task queues", borderColor: "border-l-[#f59e0b]" },
    { icon: "Search", query: "Top Python libraries for PDF parsing", borderColor: "border-l-[#8b5cf6]" },
  ],
  compare: [
    { icon: "GitCompare", query: "Compare FastAPI vs Django vs Flask", borderColor: "border-l-[#6366f1]" },
    { icon: "GitCompare", query: "Compare requests vs httpx vs aiohttp", borderColor: "border-l-[#10b981]" },
    { icon: "GitCompare", query: "Compare SQLAlchemy vs Django ORM vs Peewee", borderColor: "border-l-[#f59e0b]" },
    { icon: "GitCompare", query: "Compare pytest vs unittest vs nose2", borderColor: "border-l-[#8b5cf6]" },
  ],
}

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

// Compare mode data for "Compare FastAPI vs Django vs Flask"
export interface FrameworkCompareData {
  name: string
  logo: string
  tagline: string
  category: string
  stars: number
  forks: number
  contributors: number
  weeklyDownloads: number
  latestVersion: string
  releaseDate: string
  pythonVersions: string
  license: string
  health: number
  // Performance
  requestsPerSec: number
  latencyMs: number
  memoryMb: number
  // Features (boolean or rating 1-5)
  asyncSupport: "native" | "partial" | "limited"
  typeHints: "native" | "partial" | "limited"
  autoDocumentation: boolean
  builtInORM: boolean
  adminPanel: boolean
  websockets: "native" | "extension" | "none"
  testing: "built-in" | "extension"
  // Ecosystem
  extensions: number
  tutorialsCount: number
  stackOverflowQuestions: number
  // Use cases
  bestFor: string[]
  notIdealFor: string[]
  // Trend
  trend: number
  trendDirection: "up" | "down" | "neutral"
  adoptionTrend: { month: string; value: number }[]
}

export const frameworkCompareData: FrameworkCompareData[] = [
  {
    name: "FastAPI",
    logo: "F",
    tagline: "Modern, fast, web framework for building APIs",
    category: "Async API Framework",
    stars: 78500,
    forks: 6200,
    contributors: 650,
    weeklyDownloads: 12500000,
    latestVersion: "0.115.0",
    releaseDate: "2 weeks ago",
    pythonVersions: "3.8+",
    license: "MIT",
    health: 97,
    requestsPerSec: 45200,
    latencyMs: 2.1,
    memoryMb: 48,
    asyncSupport: "native",
    typeHints: "native",
    autoDocumentation: true,
    builtInORM: false,
    adminPanel: false,
    websockets: "native",
    testing: "built-in",
    extensions: 320,
    tutorialsCount: 8500,
    stackOverflowQuestions: 24800,
    bestFor: ["APIs", "Microservices", "ML/AI backends", "Real-time apps"],
    notIdealFor: ["Full-stack apps", "Content sites", "Beginners"],
    trend: 42,
    trendDirection: "up",
    adoptionTrend: [
      { month: "Mar", value: 8200000 },
      { month: "Jun", value: 9800000 },
      { month: "Sep", value: 11200000 },
      { month: "Dec", value: 12500000 },
    ],
  },
  {
    name: "Django",
    logo: "D",
    tagline: "The web framework for perfectionists with deadlines",
    category: "Full-Stack Framework",
    stars: 81200,
    forks: 31500,
    contributors: 2450,
    weeklyDownloads: 9800000,
    latestVersion: "5.1.2",
    releaseDate: "3 weeks ago",
    pythonVersions: "3.10+",
    license: "BSD-3",
    health: 95,
    requestsPerSec: 12800,
    latencyMs: 8.4,
    memoryMb: 125,
    asyncSupport: "partial",
    typeHints: "partial",
    autoDocumentation: false,
    builtInORM: true,
    adminPanel: true,
    websockets: "extension",
    testing: "built-in",
    extensions: 4800,
    tutorialsCount: 45000,
    stackOverflowQuestions: 312000,
    bestFor: ["Full-stack apps", "Content sites", "E-commerce", "Enterprise"],
    notIdealFor: ["Simple APIs", "Microservices", "Serverless"],
    trend: 5,
    trendDirection: "neutral",
    adoptionTrend: [
      { month: "Mar", value: 9200000 },
      { month: "Jun", value: 9400000 },
      { month: "Sep", value: 9600000 },
      { month: "Dec", value: 9800000 },
    ],
  },
  {
    name: "Flask",
    logo: "Fl",
    tagline: "A lightweight WSGI micro web framework",
    category: "Micro Framework",
    stars: 68900,
    forks: 16200,
    contributors: 720,
    weeklyDownloads: 28500000,
    latestVersion: "3.1.0",
    releaseDate: "1 month ago",
    pythonVersions: "3.8+",
    license: "BSD-3",
    health: 88,
    requestsPerSec: 18500,
    latencyMs: 5.2,
    memoryMb: 32,
    asyncSupport: "limited",
    typeHints: "partial",
    autoDocumentation: false,
    builtInORM: false,
    adminPanel: false,
    websockets: "extension",
    testing: "extension",
    extensions: 2100,
    tutorialsCount: 52000,
    stackOverflowQuestions: 98500,
    bestFor: ["Small apps", "Prototypes", "Learning", "Flexibility"],
    notIdealFor: ["Large apps", "Real-time", "High performance APIs"],
    trend: 3,
    trendDirection: "down",
    adoptionTrend: [
      { month: "Mar", value: 29500000 },
      { month: "Jun", value: 29200000 },
      { month: "Sep", value: 28800000 },
      { month: "Dec", value: 28500000 },
    ],
  },
]

export const compareStatCards = [
  { label: "Frameworks Analyzed", value: 3, type: "number" as const },
  { label: "Combined Stars", value: 228600, type: "number" as const },
  {
    label: "Most Downloaded",
    value: "Flask",
    sub: "28.5M weekly",
    type: "text" as const,
  },
  {
    label: "Fastest Growing",
    value: "FastAPI",
    sub: "42% YoY",
    type: "growth" as const,
  },
]

export const compareAiSynthesis = {
  summary:
    "Based on analysis of 3 major Python web frameworks across performance benchmarks, ecosystem health, and real-world adoption patterns:",
  recommendation:
    "**FastAPI** is the clear winner for new API-first projects requiring high performance and modern Python features (async/await, type hints). Choose **Django** for full-stack applications needing batteries-included features like admin panel, ORM, and authentication. **Flask** remains excellent for learning, prototyping, or when you need maximum flexibility, but its sync-first design shows declining adoption for new projects.",
  dataSources: [
    "PyPI download statistics (last 12 months)",
    "GitHub repository metrics",
    "TechEmpower Web Framework Benchmarks",
    "Stack Overflow Developer Survey 2024",
  ],
  followUps: [
    {
      text: "Show me FastAPI vs Flask performance benchmarks",
      borderColor: "border-l-[#6366f1]",
    },
    {
      text: "Which has better async support for WebSockets?",
      borderColor: "border-l-[#10b981]",
    },
    {
      text: "Compare learning curves for beginners",
      borderColor: "border-l-[#f59e0b]",
    },
  ],
}
