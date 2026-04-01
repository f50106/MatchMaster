"""Career Progression Scorer — evaluates career growth from title seniority levels.

v4 (2026-04-01): Tolerates minor level drops (±1) as lateral moves.
Cross-company title inflation means "Lead" at small company ≈ "Specialist"
at an enterprise. Only ≥2 level drops count as true demotions.
"""

from __future__ import annotations

from app.domain.entities.dimension_score import DimensionScore
from app.domain.entities.job_description import ParsedJD
from app.domain.entities.resume import ParsedResume
from app.domain.scorers._constants import get_seniority_level
from app.domain.scorers.base import BaseScorer

# A drop of exactly 1 level between jobs is treated as lateral (→), not demotion (↓).
# Reason: title inflation across companies means "Project Lead" at outsourcing firm
# ≈ "Senior Specialist" at enterprise. Only ≥2 level drops are genuine demotions.
_LATERAL_TOLERANCE = 1


class CareerProgressionScorer(BaseScorer):
    dimension = "career_progression"

    async def score(self, jd: ParsedJD, resume: ParsedResume) -> DimensionScore:
        evidence: list[str] = []
        exps = resume.work_experiences

        if len(exps) == 0:
            return DimensionScore(
                dimension=self.dimension,
                score=0.0,
                weight=0.6,
                details="No work experience — cannot assess progression",
                evidence=["No work experience entries found"],
            )

        if len(exps) == 1:
            return DimensionScore(
                dimension=self.dimension,
                score=45.0,
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

        up = 0
        stable = 0        # same level (0 credit: 0.5)
        minor_down = 0     # ↓1 level: neutral (0 credit)
        down = 0           # ↓2+ levels: demotion penalty (-0.5 credit)
        for i in range(1, len(chrono)):
            diff = chrono[i][1] - chrono[i - 1][1]
            if diff > 0:
                up += 1
            elif diff == 0:
                stable += 1
            elif diff >= -_LATERAL_TOLERANCE:
                minor_down += 1
            else:
                down += 1

        steps = len(chrono) - 1

        progress_raw = (up * 1.0 + stable * 0.5 - down * 0.5) / steps if steps else 0.5
        progress = max(0.0, min(1.0, progress_raw))
        raw = 0.3 + 0.7 * progress

        max_level = max(lvl for _, lvl in levels)
        # Seniority bonus ONLY for net-positive careers — declining executives
        # should not get free points for past titles
        if up > down:
            if max_level >= 6:
                raw = min(1.0, raw + 0.10)
            elif max_level >= 5:
                raw = min(1.0, raw + 0.05)

        evidence.append(f"↑{up} →{stable} ↘{minor_down} ↓{down}")
        evidence.append(" → ".join(f"{t} (Lv{l})" for t, l in chrono))

        return DimensionScore(
            dimension=self.dimension,
            score=round(raw * 100, 1),
            weight=0.6,
            details=f"↑{up} →{stable} ↘{minor_down} ↓{down} (max lv {max_level})",
            evidence=evidence,
        )
