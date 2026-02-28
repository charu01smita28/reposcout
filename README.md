# RepoScout — The Open Source Intelligence Engine

> **"RepoScout is the first intelligence engine built on top of the entire open source ecosystem. It doesn't guess — it knows."**

Query **85K+ actively maintained packages** with real-time stats, **YoY growth trends**, and **rich metadata** from PyPI. Real data, not opinions.

RepoScout is an AI-powered research tool that helps developers make data-driven decisions about open source packages. Instead of relying on blog posts, Reddit threads, or ChatGPT's training data, RepoScout queries a pre-indexed dataset of the PyPI ecosystem — enriched with full README descriptions, keywords, classifiers, version history, and live GitHub metadata — and combines it with AI-powered code analysis via Mistral AI.

---

## Why RepoScout?

| Capability | ChatGPT | GitHub Search | RepoScout |
|---|---|---|---|
| "How many projects use FastAPI?" | Guesses from training data | Can't answer | **Exact number from indexed data** |
| "Is library X actively maintained?" | Outdated info | Manual checking | **Real-time health score** |
| "What's growing fastest in Python ML?" | Generic answer | Can't analyze trends | **Computed from YoY growth data** |
| "Compare implementation patterns" | General knowledge | Keyword file matches | **Actual code analysis + adoption data** |
| Dependency graph traversal | Impossible | Impossible | **Native capability** |

**The data moat:** RepoScout has a queryable database of package metadata, dependency relationships, and rich descriptions that no LLM has been trained on.

---

## Core Features

### 1. "How does the world solve X?"

> **Example:** "How do Python projects handle rate limiting?"

RepoScout runs semantic search across 85K+ package descriptions (full READMEs, keywords, classifiers), queries the dependency graph for adoption stats, fetches actual source code from top packages via GitHub, and synthesizes a comparison with real numbers.

**What you get:**
- "47 Python packages relate to rate limiting"
- "234,500 total dependents across them"
- "ratelimit is most popular (12,400 dependents), but slowapi is growing 312% YoY"
- Comparison table with health scores
- Actual code snippet from the recommended package
- AI-synthesized recommendation based on the data

### 2. "Should I use library X or Y?"

> **Example:** "FastAPI vs Django for a new API project?"

Pulls structured data for both packages, compares dependents count, YoY growth trajectory, maintainer activity, version frequency, and stars. Computes health scores, fetches code samples showing usage patterns, and gives a data-backed recommendation.

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
│                    THREE-LAYER DATA STACK                     │
│                                                              │
│  LAYER 2 — Fresh Ecosystem Snapshot (deps.dev + PyPI)        │
│  ├── packages ──────── 85K packages (stars, forks, growth)   │
│  ├── pypi_metadata ─── 85K (README, keywords, classifiers,  │
│  │                      versions, license, dependencies)     │
│  └── growth data ───── YoY growth % (2025 vs 2026)          │
│                                                              │
│  LAYER 1 — Historical Graph (Libraries.io) [Future Extension]│
│  ├── lib_projects ──── 400K PyPI packages                    │
│  ├── lib_deps ──────── 235M dependency relationships         │
│  └── lib_versions ──── version history with timestamps       │
│                                                              │
│  LAYER 3 — Live Intelligence (per-request)                   │
│  ├── PyPI JSON API ── real-time metadata                     │
│  ├── GitHub raw URLs ── source code fetching                 │
│  └── Qdrant Cloud ── semantic search (Mistral Embed, 1024d)  │
└──────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Component | Technology | Role |
|-----------|-----------|------|
| Frontend | Next.js, shadcn/ui | Search UI, charts, health visualizations |
| Backend | Python, FastAPI | API server, agent coordination |
| Structured Data | DuckDB | Package stats, comparisons, growth trends |
| Rich Metadata | PyPI API bulk fetch | README descriptions, keywords, classifiers, versions |
| Semantic Search | Qdrant Cloud + Mistral Embed | Natural language package discovery (80K+ vectors) |
| Orchestration | Mistral Large | Query classification, function calling, synthesis |
| Code Analysis | Devstral | Source code pattern extraction |
| Live Data | PyPI API, GitHub Raw URLs | Fresh metadata + source code |

---

## UI Features

- **Stats Dashboard** — Packages found, total dependents, most popular, fastest growing
- **Comparison Tables** — Side-by-side metrics with health indicators, stars, and trend arrows
- **RepoScout Score Rings** — Color-coded 0-100 health metric for every package
- **Adoption Charts** — Horizontal bar charts showing real dependent counts
- **Growth Trend Lines** — YoY growth percentages with visual indicators
- **Implementation Patterns** — Syntax-highlighted code blocks pulled from actual source files
- **AI Analysis** — Data-backed synthesis with suggested follow-up questions

---

## Data Architecture

RepoScout uses a three-layer data architecture:

| Layer | Source | What's in DuckDB | Rows |
|-------|--------|-------------------|------|
| **Layer 2** | deps.dev (BigQuery) + PyPI API | `packages` (stats, growth), `pypi_metadata` (READMEs, keywords, versions) | 85K each |
| **Layer 1** | Libraries.io 2020 | `lib_projects`, `lib_deps`, `lib_versions` | 400K / 235M / 2M |
| **Layer 3** | PyPI API + GitHub + Qdrant Cloud | Live per-request + semantic search | On demand + 80K vectors |

Layer 2 is primary (fresh, rich data). Layer 3 adds live intelligence + semantic search via Qdrant Cloud (Mistral Embed, 1024 dimensions). Layer 1 is a future extension for historical dependency graph analysis.

## Setup

```bash
# Install dependencies
pip install -r backend/requirements.txt

# Set environment variables
cp .env.example .env
# Add MISTRAL_API_KEY, QDRANT_URL, QDRANT_API_KEY

# Build the database
# 1. Place BigQuery exports in data/layer2/ (dependents.csv, bridge.csv, projects.csv)
python scripts/setup_layer2.py                    # ~1 min

# 2. Add growth trends
# Place dependents_2025.csv in data/layer2/
python scripts/add_growth_data.py                 # ~10 sec

# 3. Fetch rich PyPI metadata (READMEs, keywords, classifiers)
python scripts/fetch_pypi_metadata.py             # ~25 min, free, cached

# 4. Generate embeddings for semantic search (Qdrant Cloud)
python scripts/generate_embeddings.py             # ~30 min, needs Mistral API key + Qdrant Cloud

# 5. (Future Extension) Add historical data from Libraries.io
# python scripts/setup_layer1.py                  # ~5 min
# python scripts/setup_layer1.py --with-deps      # ~30 min for full dep graph

# Start backend
uvicorn backend.main:app --reload --port 8000

# Start frontend (in another terminal)
cd frontend && pnpm install && pnpm dev
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

## Embedding Pipeline

RepoScout uses a custom text cleaning pipeline to generate high-quality embeddings from PyPI package metadata:

1. **Text Extraction** — For each package, we build embedding text from:
   - Package name + summary
   - Keywords (when available)
   - Classifier-derived metadata: frameworks, topics, environment
   - Meaningful README sections (extracted by heading-title matching)

2. **README Cleaning** (7-phase pipeline in `scripts/text_cleaner.py`):
   - Code block extraction → HTML removal → Badge removal → Boilerplate section removal → URL removal → Markdown formatting strip → Whitespace cleanup

3. **Section Extraction** — Instead of embedding raw READMEs, we parse headings and extract only semantically useful sections ("Features", "Overview", "What is it", "Dependencies", etc.)

4. **Vectorization** — Mistral Embed (1024 dimensions) encodes the cleaned text, stored in Qdrant Cloud with lean payload metadata for fast retrieval

**Result:** ~50-500 tokens of clean, semantically rich text per package across 80K+ vectors.

---

## Data Sources

- [**Google deps.dev**](https://deps.dev/) — fresh package stats via BigQuery (primary data source)
- [**PyPI JSON API**](https://pypi.org) — rich metadata: full README, keywords, classifiers, version history
- [**Libraries.io Open Data**](https://zenodo.org/record/3626071) — historical dependency graph (400K packages, 235M relationships)
- **GitHub Raw URLs** — source code fetching (no API rate limits)

## License

MIT
