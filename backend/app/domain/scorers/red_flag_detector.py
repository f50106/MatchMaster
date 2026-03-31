"""Red Flag Detector — regex rules for short tenure, gaps, missing info.

v4 (2026-03-31): Tenure recency weighting + contract/consultant distinction.
- Recent short tenures (last 3 years) carry 2× penalty
- Old short tenures (>3 years ago) carry 0.5× penalty
- Contract/consultant/freelance titles discount penalty by 50%
"""

from __future__ import annotations

import re
from datetime import datetime

from app.domain.entities.dimension_score import DimensionScore
from app.domain.entities.job_description import ParsedJD
from app.domain.entities.resume import ParsedResume
from app.domain.scorers.base import BaseScorer

_SHORT_TENURE_MONTHS = 10  # < 10 months = short tenure (industry norm: 1yr min)
_GAP_MONTHS = 6  # > 6 months gap = flag

# Recency weighting: how much more/less recent vs old short tenures matter
_RECENCY_YEARS = 3          # "recent" = ended within this many years
_RECENT_MULTIPLIER = 2.0    # recent short stint = 2× penalty
_OLD_MULTIPLIER = 0.5       # old short stint = 0.5× penalty

# Contract/consultant role discount
_CONTRACT_PATTERNS = re.compile(
    r'\b(contract|contractor|consultant|consulting|freelance|outsourc)',
    re.IGNORECASE,
)
_CONTRACT_DISCOUNT = 0.5    # contract roles halve the short tenure penalty

# Base penalties per short tenure count (before recency/contract weighting)
_BASE_PENALTY_PER_STINT = 4.0  # each short stint's base penalty


def _is_recent(end_date: str, ref_year: int) -> bool:
    """Check if an end_date falls within _RECENCY_YEARS of ref_year."""
    if not end_date or end_date.lower() in ("present", "current", "now"):
        return True  # still employed → definitely recent
    try:
        # Parse YYYY-MM or YYYY
        parts = end_date.split("-")
        end_year = int(parts[0])
        return (ref_year - end_year) <= _RECENCY_YEARS
    except (ValueError, IndexError):
        return True  # can't parse → assume recent (safer)


def _is_contract_role(title: str) -> bool:
    """Check if title indicates a contract/consultant/freelance role."""
    return bool(_CONTRACT_PATTERNS.search(title))


class RedFlagDetector(BaseScorer):
    dimension = "red_flags"

    async def score(self, jd: ParsedJD, resume: ParsedResume) -> DimensionScore:
        flags: list[str] = []
        penalty = 0.0
        ref_year = datetime.now().year

        # 1. Short tenure detection — with recency weighting + contract discount
        short_tenure_count = 0
        short_tenure_weighted_penalty = 0.0
        for exp in resume.work_experiences:
            if exp.duration_months is not None and exp.duration_months < _SHORT_TENURE_MONTHS:
                short_tenure_count += 1

                # Recency multiplier
                recent = _is_recent(exp.end_date, ref_year)
                recency_mult = _RECENT_MULTIPLIER if recent else _OLD_MULTIPLIER

                # Contract/consultant discount
                contract = _is_contract_role(exp.title)
                contract_mult = _CONTRACT_DISCOUNT if contract else 1.0

                effective_penalty = _BASE_PENALTY_PER_STINT * recency_mult * contract_mult
                short_tenure_weighted_penalty += effective_penalty

                tag_parts: list[str] = []
                if recent:
                    tag_parts.append("recent")
                if contract:
                    tag_parts.append("contract")
                tag = f" [{', '.join(tag_parts)}]" if tag_parts else ""
                flags.append(
                    f"Short tenure: {exp.company} ({exp.duration_months}mo){tag}"
                )

        # Cluster penalty: 3+ short stints = additional compounding
        if short_tenure_count >= 3:
            short_tenure_weighted_penalty *= 1.5  # 50% surcharge for pattern
        elif short_tenure_count >= 2:
            short_tenure_weighted_penalty *= 1.2  # 20% surcharge

        penalty += short_tenure_weighted_penalty

        # 2. Employment gaps
        dates: list[tuple[str, str]] = []
        for exp in resume.work_experiences:
            if exp.end_date and exp.start_date:
                dates.append((exp.start_date, exp.end_date))

        # Simple gap detection via sorted date strings
        dates.sort(key=lambda x: x[0])
        for i in range(1, len(dates)):
            prev_end = dates[i - 1][1]
            curr_start = dates[i][0]
            if prev_end < curr_start:
                flags.append(f"Gap: {prev_end} → {curr_start}")
                penalty += 5

        # 3. Missing critical info
        missing_sections = 0
        if not resume.candidate_name:
            flags.append("Missing: candidate name")
            penalty += 5    # mild — anonymised resumes are common
            missing_sections += 1
        if not resume.work_experiences:
            flags.append("Missing: work experience")
            penalty += 20   # major — no work history at all
            missing_sections += 1
        if not resume.education:
            flags.append("Missing: education")
            penalty += 10   # moderate — self-taught is valid in tech
            missing_sections += 1
        if not resume.skills:
            flags.append("Missing: skills")
            penalty += 15   # moderate — some formats embed skills in descriptions
            missing_sections += 1

        # Compound penalty: the MORE sections missing, the worse the signal
        if missing_sections >= 4:
            flags.append("Critical: resume appears empty or unreadable")
            penalty += 50   # all sections missing = blank page
        elif missing_sections >= 3:
            flags.append("Warning: severely incomplete resume")
            penalty += 20   # 3 of 4 missing = very sparse

        # Score = 100 - penalty (clamped to 0-100)
        final_score = max(0, min(100, 100 - penalty))

        return DimensionScore(
            dimension=self.dimension,
            score=round(final_score, 1),
            weight=0.8,
            details=f"{len(flags)} flag(s), penalty: -{penalty}",
            evidence=flags,
        )
