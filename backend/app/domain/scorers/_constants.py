"""Shared constants for scorer modules."""

from __future__ import annotations

SENIORITY_KEYWORDS: dict[str, int] = {
    # Level 1: Entry / Intern
    "intern": 1, "trainee": 1, "apprentice": 1,
    # Level 2: Junior / Associate
    "junior": 2, "associate": 2, "graduate": 2,
    # Level 3: Mid-level (default for unrecognised titles)
    "mid": 3, "engineer": 3, "developer": 3, "analyst": 3,
    "programmer": 3, "consultant": 3,
    # Level 4: Senior / Specialist
    "senior": 4, "specialist": 4, "sr.": 4, "sr ": 4,
    # Level 5: Lead / Principal / Staff / Architect / Manager
    "lead": 5, "principal": 5, "staff": 5, "manager": 5,
    "architect": 5, "tech lead": 5,
    # Level 6: Head / Director
    "head": 6, "director": 6,
    # Level 7-8: Executive
    "vp": 7, "vice president": 7,
    "chief": 8, "cto": 8, "ceo": 8, "cio": 8,
    # Chinese equivalents
    "實習": 1, "助理": 2, "初級": 2,
    "中級": 3,
    "資深": 4, "高級": 4, "專員": 4,
    "主管": 5, "經理": 5, "架構師": 5,
    "總監": 6, "副總": 7,
}


def get_seniority_level(title: str, default: int = 3) -> int:
    """Return the highest seniority level found in a job title string.

    Scans for all matching keywords and returns the highest level found.
    This ensures "Lead Software Engineer" → 5 (Lead), not 3 (Engineer).
    """
    title_lower = title.lower()
    level = default
    for keyword, lvl in SENIORITY_KEYWORDS.items():
        if keyword in title_lower and lvl > level:
            level = lvl
    return level
