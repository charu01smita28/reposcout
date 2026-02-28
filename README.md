# RepoScout — The Open Source Intelligence Engine

> **"RepoScout is the first intelligence engine built on top of the entire open source ecosystem. It doesn't guess — it knows."**

Query **2.6M packages** and **235M dependency relationships**. Real data, not opinions.

RepoScout is an AI-powered research tool that helps developers make data-driven decisions about open source packages. Instead of relying on blog posts, Reddit threads, or ChatGPT's training data, RepoScout queries a pre-indexed dataset of the entire PyPI ecosystem — data no LLM has access to — and combines it with live GitHub code analysis powered by Mistral AI.

---

## Why RepoScout?

| Capability | ChatGPT | GitHub Search | RepoScout |
|---|---|---|---|
| "How many projects use FastAPI?" | Guesses from training data | Can't answer | **Exact number from indexed data** |
| "Is library X actively maintained?" | Outdated info | Manual checking | **Real-time health score** |
| "What's growing fastest in Python ML?" | Generic answer | Can't analyze trends | **Computed from 235M relationships** |
| "Compare implementation patterns" | General knowledge | Keyword file matches | **Actual code analysis + adoption data** |
| Dependency graph traversal | Impossible | Impossible | **Native capability** |

**The data moat:** RepoScout has a queryable database of package metadata and dependency relationships that no LLM has been trained on.

---

## Core Features

### 1. "How does the world solve X?"

> **Example:** "How do Python projects handle rate limiting?"

RepoScout runs semantic search across 2.6M package descriptions, queries the dependency graph for adoption stats, fetches actual source code from top packages via GitHub, and synthesizes a comparison with real numbers.

**What you get:**
- "47 Python packages relate to rate limiting"
- "234,500 total dependents across them"
- "ratelimit is most popular (12,400 dependents), but slowapi is growing 312% YoY"
- Comparison table with health scores
- Actual code snippet from the recommended package
- AI-synthesized recommendation based on the data

### 2. "Should I use library X or Y?"

> **Example:** "FastAPI vs Django for a new API project?"

Pulls structured data for both packages, compares dependents count, growth trajectory, maintainer activity, version frequency, and stars. Computes health scores, fetches code samples showing usage patterns, and gives a data-backed recommendation.

### 3. "Is this dependency safe?"

> **Example:** "Should I use python-jose?"

Pulls package metadata (maintainers, last release, commit frequency, dependents), computes a proprietary **RepoScout Score (0-100)**, flags risks like inactive maintainers or stale releases, and automatically suggests healthier alternatives.

### 4. Implementation Patterns

Fetches real source code from top packages and uses Devstral to extract best-practice implementation patterns — so you see exactly how to use a library, not just which one to pick.

---

## RepoScout Score

Every package gets a proprietary health score from 0-100.

| Weight | Factor | What it measures |
|--------|--------|-----------------|
| 35% | **Adoption** | Real-world usage — log-scaled dependents count |
| 30% | **Maintenance** | How recently the package was updated |
| 15% | **Maturity** | Version count as a proxy for stability |
| 20% | **Community** | Stars + forks as engagement signal |

- **80-100** — Healthy (green)
- **60-79** — Moderate (yellow)
- **0-59** — Caution (red)

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     NEXT.JS + SHADCN UI                      │
│                                                              │
│  Search bar + mode tabs · Stats cards · Comparison table     │
│  Adoption charts · Growth trends · Code snippets             │
│  Health score rings · AI analysis · Follow-up suggestions    │
└─────────────────────────────┬────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                     FASTAPI BACKEND                          │
│                                                              │
│  POST /api/search         GET /api/package/{name}            │
│  GET  /api/compare        GET /api/health/{name}             │
│  GET  /api/stats          GET /api/dependents/{name}         │
└─────────────────────────────┬────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                   MISTRAL AI AGENT LAYER                     │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐     │
│  │              ORCHESTRATOR (Mistral Large)            │     │
│  │  Classifies query → routes to agents → coordinates  │     │
│  │  multi-step research via function calling           │     │
│  └──────┬──────────────┬──────────────┬────────────────┘     │
│         │              │              │                       │
│         ▼              ▼              ▼                       │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐               │
│  │  PACKAGE   │ │    CODE    │ │ SYNTHESIS  │               │
│  │   INTEL    │ │  RESEARCH  │ │   AGENT    │               │
│  │            │ │            │ │            │               │
│  │ DuckDB    │ │ GitHub raw │ │ Combines   │               │
│  │ queries   │ │ URL fetch  │ │ all data   │               │
│  │ Qdrant    │ │ Devstral   │ │ Generates  │               │
│  │ search    │ │ code       │ │ analysis   │               │
│  │ Health    │ │ analysis   │ │ Recommends │               │
│  │ scores    │ │            │ │            │               │
│  └────────────┘ └────────────┘ └────────────┘               │
└─────────────────────────────┬────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                       DATA LAYER                             │
│                                                              │
│  DuckDB (structured queries)                                 │
│  ├── projects ──── 2.6M packages (Libraries.io + deps.dev)  │
│  ├── deps ──────── 235M dependency relationships             │
│  └── versions ──── version history with timestamps           │
│                                                              │
│  Qdrant (semantic search)                                    │
│  └── 400K+ Python package description embeddings             │
│                                                              │
│  Live Sources                                                │
│  ├── PyPI JSON API ── fresh metadata supplement              │
│  └── GitHub raw URLs ── source code fetching                 │
└──────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Component | Technology | Role |
|-----------|-----------|------|
| Frontend | Next.js, shadcn/ui, Plotly | Search UI, charts, health visualizations |
| Backend | Python, FastAPI | API server, agent coordination |
| Structured Data | DuckDB | 2.6M packages, 235M dependency queries |
| Semantic Search | Qdrant + Mistral Embed | Natural language package discovery |
| Orchestration | Mistral Large | Query classification, function calling, synthesis |
| Code Analysis | Devstral | Source code pattern extraction |
| Live Data | PyPI API, GitHub Raw URLs | Fresh metadata + source code |

---

## UI Features

- **Stats Dashboard** — Packages found, total dependents, most popular, fastest growing
- **Comparison Tables** — Side-by-side metrics with health indicators, stars, and trend arrows
- **RepoScout Score Rings** — Color-coded 0-100 health metric for every package
- **Adoption Charts** — Horizontal bar charts showing real dependent counts
- **Growth Trend Lines** — Line charts tracking package adoption over time
- **Implementation Patterns** — Syntax-highlighted code blocks pulled from actual source files
- **AI Analysis** — Data-backed synthesis with suggested follow-up questions

---

## Setup

```bash
# Install dependencies
pip install -r backend/requirements.txt

# Set environment variables
cp .env.example .env
# Add MISTRAL_API_KEY and GITHUB_TOKEN

# Load data into DuckDB
python -m scripts.load_librariesio              # projects + versions (~5 min)
python -m scripts.load_librariesio --with-deps  # + dependency graph (~30 min)

# Load fresh BigQuery data (optional)
python -m scripts.load_bigquery

# Generate embeddings for semantic search
python -m scripts.generate_embeddings --limit 50000

# Start backend
uvicorn backend.main:app --reload --port 8000

# Start frontend (in another terminal)
cd frontend && npm run dev
```

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/search` | Main query — runs the full agent pipeline |
| `GET` | `/api/package/{name}` | Package stats + health score |
| `GET` | `/api/compare?packages=a,b` | Side-by-side comparison |
| `GET` | `/api/health/{name}` | Health check with risk flags |
| `GET` | `/api/stats` | Dataset statistics |
| `GET` | `/api/search/quick` | Fast semantic search |
| `GET` | `/api/dependents/{name}` | Reverse dependency lookup |

## Data Sources

- [**Libraries.io Open Data**](https://zenodo.org/record/3626071) — 2.6M packages, 235M dependency relationships (CC license)
- [**Google deps.dev**](https://deps.dev/) — supplementary fresh package data via BigQuery
- [**PyPI JSON API**](https://pypi.org) — live metadata for current package versions
- **GitHub Raw URLs** — source code fetching (no API rate limits)

## License

MIT
