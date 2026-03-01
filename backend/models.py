"""
RepoScout data models.

Defines the schema for what's stored where:
- DuckDB: source of truth (packages + pypi_metadata tables)
- Qdrant: semantic search only (vector + lean payload)
"""

from pydantic import BaseModel


# ─── Qdrant Payload (stored alongside vector, returned on search) ───

class QdrantPayload(BaseModel):
    """Metadata stored in Qdrant payload.
    Includes embedding_text so the dashboard shows what was actually embedded."""
    name: str
    summary: str = ""
    stars: int = 0
    dependent_count: int = 0
    growth_pct: float = 0.0
    version: str = ""
    embedding_text: str = ""


# ─── Qdrant Search Result ───

class SemanticSearchResult(BaseModel):
    """What comes back from a Qdrant semantic search."""
    name: str
    summary: str = ""
    stars: int = 0
    dependent_count: int = 0
    growth_pct: float = 0.0
    version: str = ""
    similarity_score: float = 0.0


# ─── DuckDB: Full Package (joined packages + pypi_metadata) ───

class PackageFull(BaseModel):
    """Full package data from DuckDB (packages JOIN pypi_metadata).
    Used for detail pages, comparisons, health checks."""
    # From packages table
    package_name: str
    dependent_count: int = 0
    stars: int = 0
    forks: int = 0
    open_issues: int = 0
    github_repo: str = ""
    growth_pct: float = 0.0
    dependent_count_2025: int = 0
    # From pypi_metadata table
    summary: str = ""
    description: str = ""          # full README — only from DuckDB
    keywords: str = ""
    classifiers: str = "[]"        # JSON string
    version: str = ""
    author: str = ""
    license: str = ""
    requires_dist: str = "[]"      # JSON string
    requires_python: str = ""
    total_versions: int = 0
    latest_release_date: str = ""
    first_release_date: str = ""
    home_page: str = ""
    # Computed
    reposcout_score: float = 0.0
    score_label: str = ""          # "Healthy" / "Moderate" / "Caution"
    days_since_last_release: int = 0


# ─── API Request/Response Models ───

class SearchRequest(BaseModel):
    query: str
    mode: str = "explore"  # "explore" | "compare"


class HealthCheckResponse(BaseModel):
    """Health check API response."""
    package_name: str
    reposcout_score: float = 0.0
    score_label: str = ""
    risks: list[str] = []
    risk_level: str = ""  # "high" | "moderate" | "low"
