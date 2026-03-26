"""Career Progression Scorer — evaluates career growth from title seniority levels."""

from __future__ import annotations

from app.domain.entities.dimension_score import DimensionScore
from app.domain.entities.job_description import ParsedJD
from app.domain.entities.resume import ParsedResume
from app.domain.scorers._constants import get_seniority_level
from app.domain.scorers.base import BaseScorer


class CareerProgressionScorer(BaseScorer):
    dimension = "career_progression"

    async def score(self, jd: ParsedJD, resume: ParsedResume) -> DimensionScore:
        evidence: list[str] = []
        exps = resume.work_experiences

        if len(exps) <= 1:
            return DimensionScore(
                dimension=self.dimension,
                score=60.0,
                weight=0.6,
                details="Single role — cannot assess progression",
                evidence=["Only 1 work experience entry"],
            )

        levels: list[tuple[str, int]] = []
        for exp in exps:
            level = get_seniority_level(exp.title)
            levels.append((exp.title, level))

        # Work experiences usually listed newest-first → reverse for chronological
        chrono = list(reversed(levels))

        up = sum(1 for i in range(1, len(chrono)) if chrono[i][1] > chrono[i - 1][1])
        stable = sum(1 for i in range(1, len(chrono)) if chrono[i][1] == chrono[i - 1][1])
        down = sum(1 for i in range(1, len(chrono)) if chrono[i][1] < chrono[i - 1][1])
        steps = len(chrono) - 1

        progress = (up * 1.0 + stable * 0.5) / steps if steps else 0.5
        raw = 0.3 + 0.7 * progress

        max_level = max(lvl for _, lvl in levels)
        if max_level >= 6:
            raw = min(1.0, raw + 0.10)
        elif max_level >= 5:
            raw = min(1.0, raw + 0.05)

        evidence.append(f"↑{up} →{stable} ↓{down}")
        evidence.append(" → ".join(t for t, _ in chrono))

        return DimensionScore(
            dimension=self.dimension,
            score=round(raw * 100, 1),
            weight=0.6,
            details=f"↑{up} →{stable} ↓{down} (max lv {max_level})",
            evidence=evidence,
        )
