"""Role-type mismatch detection.

Classifies JD and candidate career into broad discipline categories
and detects when the candidate's primary discipline does not match the JD.
"""

from __future__ import annotations

import re

# ── Discipline taxonomy ──
# Each discipline maps to a set of title keywords that indicate that discipline.
# Order matters: more specific patterns first.

_DISCIPLINE_PATTERNS: dict[str, list[str]] = {
    "qa": [
        "qa", "quality assurance", "quality engineer", "test engineer",
        "sdet", "tester", "test lead", "test manager", "automation engineer",
        "test architect", "testing", "test analyst", "quality analyst",
        "品質", "測試", "品保",
    ],
    "devops": [
        "devops", "site reliability", "sre", "platform engineer",
        "infrastructure engineer", "cloud engineer", "release engineer",
        "維運", "運維",
    ],
    "data": [
        "data engineer", "data scientist", "data analyst", "ml engineer",
        "machine learning", "bi analyst", "bi developer", "etl",
        "資料工程", "資料科學",
    ],
    "design": [
        "ui designer", "ux designer", "ui/ux", "ux/ui", "product designer",
        "graphic designer", "visual designer", "interaction designer",
        "設計師",
    ],
    "pm": [
        "project manager", "program manager", "scrum master",
        "product manager", "product owner", "delivery manager",
        "專案經理", "產品經理",
    ],
    "development": [
        "software engineer", "software developer", "developer",
        "full stack", "fullstack", "full-stack",
        "frontend", "front-end", "front end",
        "backend", "back-end", "back end",
        "web developer", "application developer", "systems developer",
        "mobile developer", "ios developer", "android developer",
        "architect", "principal engineer", "staff engineer",
        "programmer", "coder", "engineering",
        "軟體工程", "開發", "工程師", "程式",
    ],
}

# Pre-compile patterns for performance
_COMPILED_PATTERNS: dict[str, list[re.Pattern]] = {
    discipline: [re.compile(re.escape(kw), re.IGNORECASE) for kw in keywords]
    for discipline, keywords in _DISCIPLINE_PATTERNS.items()
}


def classify_title(title: str) -> str | None:
    """Classify a job title into a discipline category.

    Returns the discipline name or None if unclassifiable.
    """
    if not title:
        return None
    title_lower = title.lower()
    for discipline, patterns in _COMPILED_PATTERNS.items():
        for pattern in patterns:
            if pattern.search(title_lower):
                return discipline
    return None


def detect_role_mismatch(
    jd_title: str,
    candidate_titles: list[str],
) -> tuple[bool, float, str]:
    """Detect whether the candidate's career discipline matches the JD.

    Args:
        jd_title: The job description title.
        candidate_titles: List of the candidate's job titles (from work experiences).

    Returns:
        (is_mismatch, mismatch_ratio, explanation)
        - is_mismatch: True if > 70% of career is in a different discipline
        - mismatch_ratio: 0.0 (perfect match) to 1.0 (complete mismatch)
        - explanation: Human-readable explanation
    """
    jd_discipline = classify_title(jd_title)
    if not jd_discipline:
        return False, 0.0, f"JD title '{jd_title}' could not be classified"

    if not candidate_titles:
        return False, 0.0, "No candidate titles to analyze"

    # Classify each candidate title
    match_count = 0
    mismatch_count = 0
    primary_disciplines: dict[str, int] = {}

    for title in candidate_titles:
        disc = classify_title(title)
        if disc is None:
            continue
        primary_disciplines[disc] = primary_disciplines.get(disc, 0) + 1
        if disc == jd_discipline:
            match_count += 1
        else:
            mismatch_count += 1

    classified_total = match_count + mismatch_count
    if classified_total == 0:
        return False, 0.0, "Could not classify candidate titles"

    mismatch_ratio = mismatch_count / classified_total

    # Determine the candidate's primary discipline
    candidate_primary = max(primary_disciplines, key=primary_disciplines.get) if primary_disciplines else None

    is_mismatch = mismatch_ratio > 0.70

    if is_mismatch and candidate_primary:
        explanation = (
            f"Role mismatch: candidate is primarily '{candidate_primary}' "
            f"({primary_disciplines.get(candidate_primary, 0)}/{classified_total} roles) "
            f"but JD requires '{jd_discipline}'. "
            f"Mismatch ratio: {mismatch_ratio:.0%}"
        )
    elif candidate_primary and candidate_primary != jd_discipline:
        explanation = (
            f"Partial mismatch: candidate has some '{candidate_primary}' background "
            f"but also has {match_count}/{classified_total} roles matching '{jd_discipline}'"
        )
    else:
        explanation = (
            f"Discipline match: {match_count}/{classified_total} roles "
            f"align with JD discipline '{jd_discipline}'"
        )

    return is_mismatch, mismatch_ratio, explanation
