"""Depth Analyzer — evaluates resume specificity, detail depth, and authenticity signals.

Detects shallow/AI-generated resumes by measuring:
1. Specificity: quantitative metrics in descriptions
2. Description density: detail richness per work experience
3. Skill-experience alignment: do listed skills actually appear in experience context?
4. Keyword stuffing: suspiciously perfect JD-skill alignment
5. Career progression: natural growth signals
6. Tool/version specificity: named tools with version numbers
"""

from __future__ import annotations

import re

from app.domain.entities.dimension_score import DimensionScore
from app.domain.entities.job_description import ParsedJD
from app.domain.entities.resume import ParsedResume
from app.domain.scorers._constants import SENIORITY_KEYWORDS, get_seniority_level
from app.domain.scorers.base import BaseScorer

# Regex patterns for quantitative / specific claims
_METRIC_PATTERNS = [
    r"\d+[%％]",                                                # percentages
    r"[\$¥￥€£]\s?\d+",                                         # currency amounts
    r"\d+\s*[KkMmBb]\b",                                       # K/M/B quantities
    r"\d+\+?\s*(?:users?|clients?|customers?|people|members?)", # people counts
    r"\d+\+?\s*(?:projects?|products?|applications?|systems?)", # project counts
    r"(?:increas|decreas|improv|reduc|gr[eo]w|boost)\w*\s.*?\d+",  # impact
    r"\b\d{1,3}(?:,\d{3})+\b",                                 # large numbers
    r"(?:ROI|revenue|profit|savings?|budget)\s.*?\d+",          # business metrics
    r"(?:用戶|客戶|團隊|成員)\s*\d+",                            # Chinese counts
    r"(?:提升|降低|增長|減少|節省|提高)\s*\d+",                    # Chinese impact
]
_METRIC_RE = re.compile("|".join(_METRIC_PATTERNS), re.IGNORECASE)

# Technology version patterns
_VERSION_RE = re.compile(
    r"(?:v|version\s?)?\d+\.\d+(?:\.\d+)*|"
    r"\b(?:python|java|node|react|angular|vue|\.net|spring|go|ruby|php|swift|kotlin)\s?\d+",
    re.IGNORECASE,
)


class DepthAnalyzer(BaseScorer):
    dimension = "depth_analysis"

    async def score(self, jd: ParsedJD, resume: ParsedResume) -> DimensionScore:
        evidence: list[str] = []
        sub_scores: list[tuple[float, float]] = []  # (score, weight)

        # ── Early exit: completely empty resume ──
        has_experience = bool(resume.work_experiences)
        has_skills = bool(resume.skills)
        if not has_experience and not has_skills:
            return DimensionScore(
                dimension=self.dimension,
                score=0.0,
                weight=0.8,
                details="No experience or skills data to analyze",
                evidence=["Resume appears empty or unreadable"],
            )

        exp_count = max(len(resume.work_experiences), 1)
        all_descriptions = " ".join(
            exp.description for exp in resume.work_experiences
        )

        # ── 1. Specificity: quantitative metrics ──
        metric_count = len(_METRIC_RE.findall(all_descriptions))
        metrics_per_exp = metric_count / exp_count

        if metrics_per_exp >= 1.5:
            specificity = 1.0
        elif metrics_per_exp >= 0.8:
            specificity = 0.85
        elif metrics_per_exp >= 0.3:
            specificity = 0.70
        elif metrics_per_exp > 0:
            specificity = 0.55
        else:
            specificity = 0.0  # no metrics at all = no specificity

        evidence.append(
            f"Specificity: {metric_count} metrics in {exp_count} roles "
            f"({metrics_per_exp:.1f}/role)"
        )
        sub_scores.append((specificity, 0.20))

        # ── 2. Description density ──
        desc_lengths = [
            len(exp.description.split()) for exp in resume.work_experiences
        ]
        avg_desc_len = sum(desc_lengths) / max(len(desc_lengths), 1)

        if avg_desc_len >= 40:
            density = 1.0
        elif avg_desc_len >= 25:
            density = 0.80
        elif avg_desc_len >= 15:
            density = 0.60
        elif avg_desc_len >= 5:
            density = 0.40
        else:
            density = 0.0  # no description content

        evidence.append(f"Desc density: avg {avg_desc_len:.0f} words/role")
        sub_scores.append((density, 0.15))

        # ── 3. Skill-experience alignment ──
        listed_skills = {s.lower().strip() for s in resume.skills}
        skills_in_context = set()
        for exp in resume.work_experiences:
            ctx = (exp.description + " " + " ".join(exp.skills_used)).lower()
            for skill in listed_skills:
                if len(skill) > 1 and skill in ctx:
                    skills_in_context.add(skill)

        if listed_skills:
            alignment_ratio = len(skills_in_context) / len(listed_skills)
        else:
            alignment_ratio = 0.0  # no skills = no alignment

        if alignment_ratio >= 0.6:
            skill_alignment = 1.0
        elif alignment_ratio >= 0.4:
            skill_alignment = 0.75
        elif alignment_ratio >= 0.2:
            skill_alignment = 0.50
        elif alignment_ratio > 0:
            skill_alignment = 0.25
        else:
            skill_alignment = 0.0

        if listed_skills and alignment_ratio < 0.2:
            evidence.append(
                f"⚠ Low alignment: skills listed but rarely in descriptions"
            )

        evidence.append(
            f"Skill-exp alignment: {len(skills_in_context)}/{len(listed_skills)} "
            f"({alignment_ratio:.0%})"
        )
        sub_scores.append((skill_alignment, 0.20))

        # ── 4. JD skill coverage (positive signal, not "stuffing") ──
        jd_skill_names = {
            s.name.lower().strip()
            for s in jd.must_have_skills + jd.nice_to_have_skills
        }
        if jd_skill_names and listed_skills:
            jd_in_resume = sum(
                1 for js in jd_skill_names if js in listed_skills
            )
            coverage_ratio = jd_in_resume / len(jd_skill_names)

            # High coverage WITH good alignment = genuine expert
            # High coverage WITHOUT alignment = possible stuffing
            if coverage_ratio > 0.90 and skill_alignment < 0.40:
                coverage_score = 0.50
                evidence.append(
                    f"⚠ Skills listed but not demonstrated in experience "
                    f"({coverage_ratio:.0%} coverage, {skill_alignment:.0%} alignment)"
                )
            else:
                # Coverage is generally positive
                coverage_score = 0.50 + 0.50 * min(coverage_ratio, 1.0)
                if coverage_ratio >= 0.70:
                    evidence.append(
                        f"✓ Strong JD coverage: {coverage_ratio:.0%} "
                        f"({jd_in_resume}/{len(jd_skill_names)})"
                    )
        elif not listed_skills:
            coverage_score = 0.0  # resume has no skills → nothing to demonstrate
        else:
            coverage_score = 0.5  # JD has no skill requirements → neutral
        sub_scores.append((coverage_score, 0.15))

        # ── 5. Career progression ──
        prog_score = self._career_progression(resume)
        evidence.append(f"Career progression: {prog_score:.0%}")
        sub_scores.append((prog_score, 0.10))

        # ── 6. Tool version specificity ──
        version_hits = _VERSION_RE.findall(
            all_descriptions + " " + " ".join(resume.skills)
        )
        if version_hits:
            version_score = min(1.0, len(version_hits) / exp_count * 0.4 + 0.5)
        else:
            version_score = 0.0  # no tool/version references
        evidence.append(f"Version specificity: {len(version_hits)} refs")
        sub_scores.append((version_score, 0.10))

        # ── Combine ──
        total_w = sum(w for _, w in sub_scores)
        raw = sum(s * w for s, w in sub_scores) / total_w
        final_score = round(raw * 100, 1)

        return DimensionScore(
            dimension=self.dimension,
            score=final_score,
            weight=0.8,
            details=(
                f"Spec={specificity:.0%} Dens={density:.0%} "
                f"Align={skill_alignment:.0%} Cover={coverage_score:.0%}"
            ),
            evidence=evidence,
        )

    @staticmethod
    def _career_progression(resume: ParsedResume) -> float:
        exps = resume.work_experiences
        if len(exps) == 0:
            return 0.0  # No data to assess
        if len(exps) == 1:
            return 0.45  # Single role — can't assess progression, neutral-conservative

        levels = [get_seniority_level(exp.title) for exp in exps]

        # Work experiences usually listed newest-first → reverse for chrono
        chrono = list(reversed(levels))
        total_steps = max(len(chrono) - 1, 1)
        up = sum(1 for i in range(1, len(chrono)) if chrono[i] > chrono[i - 1])
        stable = sum(1 for i in range(1, len(chrono)) if chrono[i] == chrono[i - 1])
        # Strict: up = full credit, stable = partial, down = 0
        progress = (up * 1.0 + stable * 0.3) / total_steps
        return min(1.0, 0.3 + 0.7 * progress)
