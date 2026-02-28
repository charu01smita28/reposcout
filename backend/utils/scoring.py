import math
from backend.config import SCORE_WEIGHTS


def compute_reposcout_score(package_data: dict) -> int:
    dependents = package_data.get("dependents_count", 0) or 0
    stars = package_data.get("stars", 0) or 0
    days = package_data.get("days_since_last_release", 9999)
    total_versions = package_data.get("total_versions", 0) or 0
    forks = package_data.get("forks", 0) or 0

    # Adoption (0-100): log-scaled dependents count
    adoption = min(100, math.log10(max(dependents, 1) + 1) * 25)

    # Maintenance (0-100): recency of last release
    if days <= 30:
        maintenance = 100
    elif days <= 90:
        maintenance = 80
    elif days <= 180:
        maintenance = 60
    elif days <= 365:
        maintenance = 40
    elif days <= 730:
        maintenance = 20
    else:
        maintenance = 5

    # Maturity (0-100): version count as stability proxy
    maturity = min(100, total_versions * 3)

    # Community (0-100): stars + forks
    community = min(100, math.log10(max(stars, 1) + 1) * 30)

    score = (
        adoption * SCORE_WEIGHTS["adoption"]
        + maintenance * SCORE_WEIGHTS["maintenance"]
        + maturity * SCORE_WEIGHTS["maturity"]
        + community * SCORE_WEIGHTS["community"]
    )

    return min(100, max(0, int(score)))


def get_score_label(score: int) -> str:
    if score >= 80:
        return "healthy"
    elif score >= 60:
        return "moderate"
    else:
        return "caution"


def get_score_color(score: int) -> str:
    if score >= 80:
        return "#22c55e"  # green
    elif score >= 60:
        return "#eab308"  # yellow
    else:
        return "#ef4444"  # red
