"""Shared constants for scorer modules."""

from __future__ import annotations

SENIORITY_KEYWORDS: dict[str, int] = {
    "intern": 1, "junior": 2, "associate": 2,
    "mid": 3, "senior": 4, "lead": 5, "principal": 5,
    "staff": 5, "manager": 5, "head": 6, "director": 6,
    "vp": 7, "chief": 8, "cto": 8, "ceo": 8,
    "實習": 1, "助理": 2, "初級": 2, "中級": 3,
    "資深": 4, "高級": 4, "主管": 5, "經理": 5,
    "總監": 6, "副總": 7,
}


def get_seniority_level(title: str, default: int = 3) -> int:
    """Return the highest seniority level found in a job title string."""
    title_lower = title.lower()
    level = default
    for keyword, lvl in SENIORITY_KEYWORDS.items():
        if keyword in title_lower and lvl > level:
            level = lvl
    return level
