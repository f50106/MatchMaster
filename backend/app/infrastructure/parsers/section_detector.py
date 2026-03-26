"""Section-aware heading detection for parsed documents."""

from __future__ import annotations

import re

# Common section headings in resumes / JDs (Chinese & English)
_SECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(
        r"^(experience|work\s*experience|employment|工作經驗|工作经验|經歷|经历)",
        re.IGNORECASE,
    ),
    re.compile(r"^(education|學歷|学历|教育)", re.IGNORECASE),
    re.compile(r"^(skills?|技能|專長|专长|technical\s*skills?)", re.IGNORECASE),
    re.compile(
        r"^(responsibilities|職責|职责|duties|job\s*description|工作內容|工作内容)",
        re.IGNORECASE,
    ),
    re.compile(r"^(requirements?|條件|条件|qualifications?|資格|资格)", re.IGNORECASE),
    re.compile(r"^(certifications?|證照|证照|licenses?)", re.IGNORECASE),
    re.compile(r"^(summary|profile|摘要|簡介|简介|about)", re.IGNORECASE),
    re.compile(r"^(projects?|專案|项目)", re.IGNORECASE),
    re.compile(r"^(languages?|語言|语言)", re.IGNORECASE),
    re.compile(r"^(benefits?|福利|compensation|薪資|薪资)", re.IGNORECASE),
]


def detect_heading_level(text: str) -> int:
    """Return heading level 1-3 if text looks like a section heading, else 0."""
    stripped = text.strip().rstrip(":：")
    if not stripped or len(stripped) > 80:
        return 0
    for pat in _SECTION_PATTERNS:
        if pat.search(stripped):
            return 1
    # Short all-caps lines
    if stripped.isupper() and len(stripped.split()) <= 6:
        return 2
    # Lines ending with colon
    if text.strip().endswith(":") and len(stripped.split()) <= 6:
        return 2
    return 0
