# RepoScout — The Open Source Intelligence Engine

> **"RepoScout doesn't guess — it knows."**

Query **85K+ Python packages**, **2M+ dependency signals**, and **360K+ download data points** to make data-driven library decisions. Powered by **4 Mistral AI models**.

RepoScout is an AI-powered research tool that helps developers choose open source packages using real ecosystem data — not blog posts, Reddit threads, or stale training data. It queries a pre-indexed snapshot of the PyPI ecosystem enriched with GitHub stats, growth trends, download history, and 80K+ semantic embeddings, then combines it with AI-powered code analysis via Mistral AI.

---

## Dataset at a Glance

| Dataset | Count | Source |
|---------|-------|--------|
| Packages indexed | **85,209** | deps.dev (BigQuery) |
| PyPI metadata (READMEs, keywords, versions) | **85,132** | PyPI JSON API |
| Download data points (daily, 6 months) | **360,984** | pypistats.org |
| Dependency relationships (requires_dist) | **584K+** | PyPI metadata |
| Aggregate dependent signals | **2.1M+** | deps.dev |
| Semantic search vectors | **80K+** | Mistral Embed → Qdrant Cloud |

---

## Why RepoScout?

| Capability | ChatGPT | GitHub Search | RepoScout |
|---|---|---|---|
| "How many projects use FastAPI?" | Guesses from training data | Can't answer | **Exact number from indexed data** |
| "Is library X actively maintained?" | Outdated info | Manual checking | **Real-time health score (0-100)** |
| "What's growing fastest in Python ML?" | Generic answer | Can't analyze trends | **Computed from YoY growth data** |
| "Show me download trends" | No data | No data | **6 months of daily PyPI downloads** |
| "Compare implementation patterns" | General knowledge | Keyword file matches | **Actual code analysis + adoption data** |

---

## Core Features

### 1. "How does the world solve X?"

> **Example:** "How do Python projects handle rate limiting?"

Runs semantic search across 85K+ package descriptions, queries adoption stats, fetches actual source code from GitHub, and synthesizes a comparison with real numbers.

### 2. "Should I use library X or Y?"

> **Example:** "FastAPI vs Django for a new API project?"

Side-by-side comparison with dependents count, YoY growth, maintainer activity, version frequency, stars, and health scores. Fetches code samples showing usage patterns.

### 3. "Is this dependency safe?"

> **Example:** "Should I use python-jose?"

Computes a **RepoScout Score (0-100)**, flags risks (inactive maintainers, stale releases), and suggests healthier alternatives.

### 4. Download Trends

Monthly download trend charts for any analyzed packages — see which libraries are gaining or losing traction over the past 6 months.

---

## 4 Mistral AI Models

| Model | Role | What it does |
|-------|------|-------------|
| **Ministral 8B** | Query Classifier | Classifies intent (explore / compare / health_check) — fast, cheap |
| **Mistral Large** | Orchestrator | Function calling with 5 tools, up to 8 iterations of research |
| **Devstral** | Code Analyst | Fetches GitHub source code and extracts implementation patterns |
| **Mistral Embed** | Semantic Search | 80K+ package embeddings (1024 dims) in Qdrant Cloud |

---

## RepoScout Score

Every package gets a health score from 0-100.

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
│  Adoption charts · Download trend lines · Code snippets      │
│  Health score rings · AI analysis · Follow-up suggestions    │
└─────────────────────────────┬────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                     FASTAPI BACKEND                          │
│                                                              │
│  POST /api/search           GET /api/package/{name}          │
│  GET  /api/compare          GET /api/health/{name}           │
│  GET  /api/downloads        GET /api/dependents/{name}       │
│  GET  /api/stats            GET /api/search/quick            │
└─────────────────────────────┬────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                   MISTRAL AI AGENT LAYER                     │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐     │
│  │         ORCHESTRATOR (Mistral Large)                 │     │
│  │  Ministral 8B classifies → Mistral Large routes     │     │
│  │  to agents → coordinates multi-step research        │     │
│  └──────┬──────────────┬──────────────┬────────────────┘     │
│         │              │              │                       │
│         ▼              ▼              ▼                       │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐               │
│  │  PACKAGE   │ │    CODE    │ │  SEMANTIC   │               │
│  │   INTEL    │ │  RESEARCH  │ │   SEARCH    │               │
│  │            │ │            │ │            │                │
│  │ DuckDB    │ │ GitHub raw │ │ Qdrant     │               │
│  │ queries   │ │ URL fetch  │ │ Cloud      │               │
│  │ PyPI API  │ │ Devstral   │ │ Mistral    │               │
│  │ Health    │ │ code       │ │ Embed      │               │
│  │ scores    │ │ analysis   │ │ (1024d)    │               │
│  └────────────┘ └────────────┘ └────────────┘               │
└─────────────────────────────┬────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                      DATA LAYER (DuckDB)                     │
│                                                              │
│  packages ─────────── 85K (stars, forks, dependents, growth) │
│  pypi_metadata ────── 85K (README, keywords, versions, deps) │
│  download_stats ───── 361K (daily downloads, 6 months)       │
│                                                              │
│  + Live: PyPI API · GitHub Raw URLs · Qdrant Cloud           │
└──────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Component | Technology | Role |
|-----------|-----------|------|
| Frontend | Next.js, shadcn/ui, Recharts | Search UI, charts, health visualizations |
| Backend | Python, FastAPI | API server, agent coordination |
| Structured Data | DuckDB | Package stats, comparisons, growth trends, downloads |
| Semantic Search | Qdrant Cloud + Mistral Embed | Natural language package discovery (80K+ vectors) |
| Orchestration | Mistral Large | Query classification, function calling, synthesis |
| Classification | Ministral 8B | Fast intent detection (explore/compare/health_check) |
| Code Analysis | Devstral | Source code pattern extraction via GitHub |
| Live Data | PyPI API, GitHub Raw URLs | Fresh metadata + source code per request |

---

## UI Features

- **Stats Dashboard** — Packages analyzed, total dependents, most popular (by stars), most depended on, fastest growing
- **Comparison Tables** — Side-by-side metrics with health indicators, stars, and trend arrows
- **RepoScout Score Rings** — Color-coded 0-100 health metric for every package
- **Adoption Charts** — Horizontal bar charts showing real dependent counts
- **Download Trend Lines** — Monthly download history (line chart, up to 5 packages)
- **Dependency Map** — Tree view of package relationships
- **AI Analysis** — Data-backed synthesis with dynamic citations (PyPI + GitHub links)
- **Follow-up Suggestions** — Contextual next queries

---

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/search` | Main query — runs the full 4-model agent pipeline |
| `GET` | `/api/package/{name}` | Package stats + health score |
| `GET` | `/api/compare?packages=a,b` | Side-by-side comparison |
| `GET` | `/api/health/{name}` | Health check with risk flags |
| `GET` | `/api/downloads?packages=a,b` | Monthly download trends |
| `GET` | `/api/stats` | Dataset statistics |
| `GET` | `/api/search/quick?q=...` | Fast semantic search |
| `GET` | `/api/dependents/{name}` | Reverse dependency lookup |

---

## Embedding Pipeline

RepoScout uses a custom text cleaning pipeline to generate high-quality embeddings:

1. **Text Extraction** — Package name + summary + keywords + classifier metadata + meaningful README sections
2. **README Cleaning** (7-phase pipeline): Code block extraction → HTML removal → Badge removal → Boilerplate removal → URL removal → Markdown strip → Whitespace cleanup
3. **Section Extraction** — Parses headings, extracts only semantically useful sections ("Features", "Overview", "Dependencies", etc.)
4. **Vectorization** — Mistral Embed (1024 dimensions) → Qdrant Cloud with lean payload metadata

**Result:** ~50-500 tokens of clean, semantically rich text per package across 80K+ vectors.

---

## Setup

```bash
# Install dependencies
pip install -r backend/requirements.txt

# Set environment variables
cp .env.example .env
# Add MISTRAL_API_KEY, QDRANT_URL, QDRANT_API_KEY

# Build the database
python scripts/setup_layer.py                # ~1 min — packages table from BigQuery CSVs
python scripts/add_growth_data.py           # ~10 sec — YoY growth percentages
python scripts/fetch_pypi_metadata.py       # ~25 min — rich PyPI metadata (cached)
python scripts/generate_embeddings.py       # ~30 min — Mistral Embed → Qdrant Cloud
python scripts/fetch_download_stats.py      # ~15 min — daily download stats from pypistats.org

# Start backend
uvicorn backend.main:app --reload --port 8000

# Start frontend (in another terminal)
cd frontend && pnpm install && pnpm dev
```

---

## Data Sources

- [**Google deps.dev**](https://deps.dev/) — fresh package stats via BigQuery (primary source)
- [**PyPI JSON API**](https://pypi.org) — rich metadata: README, keywords, classifiers, versions
- [**pypistats.org**](https://pypistats.org/) — daily download statistics (6 months)
- **GitHub Raw URLs** — source code fetching for code analysis

---

## License

Apache 2.0
