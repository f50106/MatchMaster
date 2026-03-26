"""Red Flag Detector — regex rules for short tenure, gaps, missing info."""

from __future__ import annotations

import re
from datetime import datetime

from app.domain.entities.dimension_score import DimensionScore
from app.domain.entities.job_description import ParsedJD
from app.domain.entities.resume import ParsedResume
from app.domain.scorers.base import BaseScorer

_SHORT_TENURE_MONTHS = 10  # < 10 months = short tenure (industry norm: 1yr min)
_GAP_MONTHS = 6  # > 6 months gap = flag


class RedFlagDetector(BaseScorer):
    dimension = "red_flags"

    async def score(self, jd: ParsedJD, resume: ParsedResume) -> DimensionScore:
        flags: list[str] = []
        penalty = 0.0

        # 1. Short tenure detection
        short_tenure_count = 0
        for exp in resume.work_experiences:
            if exp.duration_months is not None and exp.duration_months < _SHORT_TENURE_MONTHS:
                short_tenure_count += 1
                flags.append(
                    f"Short tenure: {exp.company} ({exp.duration_months}mo)"
                )

        if short_tenure_count >= 3:
            penalty += 15
        elif short_tenure_count >= 2:
            penalty += 8
        elif short_tenure_count >= 1:
            penalty += 4

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
        if not resume.candidate_name:
            flags.append("Missing: candidate name")
            penalty += 5
        if not resume.work_experiences:
            flags.append("Missing: work experience")
            penalty += 15
        if not resume.education:
            flags.append("Missing: education")
            penalty += 5
        if not resume.skills:
            flags.append("Missing: skills")
            penalty += 10

        # Score = 100 - penalty (clamped to 0-100)
        final_score = max(0, min(100, 100 - penalty))

        return DimensionScore(
            dimension=self.dimension,
            score=round(final_score, 1),
            weight=0.8,
            details=f"{len(flags)} flag(s), penalty: -{penalty}",
            evidence=flags,
        )
