"""Experience Calculator — years + relevant industry + role-type awareness."""

from __future__ import annotations

from app.domain.entities.dimension_score import DimensionScore
from app.domain.entities.job_description import ParsedJD
from app.domain.entities.resume import ParsedResume
from app.domain.scorers.base import BaseScorer
from app.domain.scorers.role_type import detect_role_mismatch

_YEARS_WEIGHT = 0.45
_INDUSTRY_WEIGHT = 0.25
_ROLE_FIT_WEIGHT = 0.30  # New: role-type relevance

# When career discipline mismatches, years in wrong discipline are
# worth this fraction of equivalent years in the correct discipline.
_MISMATCH_YEAR_DISCOUNT = 0.15


class ExperienceCalculator(BaseScorer):
    dimension = "experience"

    async def score(self, jd: ParsedJD, resume: ParsedResume) -> DimensionScore:
        evidence: list[str] = []

        # Early exit: no work experience at all
        if not resume.work_experiences and not resume.total_years_experience:
            return DimensionScore(
                dimension=self.dimension,
                score=0.0,
                weight=1.5,
                details="No work experience data found",
                evidence=["Missing: work experience"],
            )

        # ── Role-type mismatch detection ──
        candidate_titles = [exp.title for exp in resume.work_experiences if exp.title]
        is_mismatch, mismatch_ratio, mismatch_explanation = detect_role_mismatch(
            jd.title, candidate_titles,
        )
        evidence.append(mismatch_explanation)

        # Role fit score: 1.0 = perfect discipline match, 0.0 = complete mismatch
        role_fit = max(0.0, 1.0 - mismatch_ratio)

        # ── Years score ──
        total_years = resume.total_years_experience or 0
        min_years = jd.experience.min_years
        preferred_years = jd.experience.preferred_years or min_years

        # If role mismatch, discount years heavily
        effective_years = total_years
        if is_mismatch:
            effective_years = total_years * _MISMATCH_YEAR_DISCOUNT
            evidence.append(
                f"Effective years discounted: {total_years:.1f}y → {effective_years:.1f}y "
                f"(discipline mismatch, {_MISMATCH_YEAR_DISCOUNT:.0%} value)"
            )

        if min_years == 0 and preferred_years == 0:
            years_ratio = 1.0  # No requirement specified
        elif effective_years >= preferred_years:
            years_ratio = 1.0
        elif effective_years >= min_years:
            years_ratio = 0.6 + 0.4 * (effective_years - min_years) / max(preferred_years - min_years, 1)
        elif effective_years > 0:
            years_ratio = 0.3 * (effective_years / max(min_years, 1))
        else:
            years_ratio = 0.0

        evidence.append(
            f"Experience: {total_years:.1f}y (effective: {effective_years:.1f}y, min: {min_years}y, preferred: {preferred_years}y)"
        )

        # ── Industry relevance ──
        target_industries = [ind.lower() for ind in jd.experience.industries]
        if not target_industries:
            industry_ratio = 0.5  # No specific industry required — true neutral
        else:
            matched = 0
            for exp in resume.work_experiences:
                if not exp.industry:
                    continue
                exp_ind = exp.industry.lower()
                for target in target_industries:
                    if target in exp_ind or exp_ind in target:
                        matched += 1
                        break
                    target_words = set(target.split())
                    exp_words = set(exp_ind.split())
                    if target_words & exp_words:
                        matched += 1
                        break
            total_exp = len(resume.work_experiences) or 1
            industry_ratio = matched / total_exp
            evidence.append(f"Industry match: {matched}/{total_exp}")

        raw = (
            years_ratio * _YEARS_WEIGHT
            + industry_ratio * _INDUSTRY_WEIGHT
            + role_fit * _ROLE_FIT_WEIGHT
        )
        final_score = round(raw * 100, 1)

        return DimensionScore(
            dimension=self.dimension,
            score=final_score,
            weight=1.5,
            details=f"Years: {years_ratio:.0%}, Industry: {industry_ratio:.0%}, Role-fit: {role_fit:.0%}",
            evidence=evidence,
        )
