"""Education Matcher — degree level + field relevance."""

from __future__ import annotations

from app.domain.entities.dimension_score import DimensionScore
from app.domain.entities.job_description import ParsedJD
from app.domain.entities.resume import ParsedResume
from app.domain.scorers.base import BaseScorer

_DEGREE_LEVELS = {
    "diploma": 1,
    "associate": 2,
    "bachelor": 3, "bachelors": 3, "b.s.": 3, "b.sc.": 3, "bs": 3, "bsc": 3,
    "b.a.": 3, "ba": 3, "b.e.": 3, "be": 3, "b.tech": 3, "btech": 3,
    "b.eng": 3, "beng": 3, "b.com": 3, "bcom": 3, "bca": 3, "bba": 3,
    "master": 4, "masters": 4, "m.s.": 4, "m.sc.": 4, "ms": 4, "msc": 4,
    "m.a.": 4, "ma": 4, "m.e.": 4, "me": 4, "m.tech": 4, "mtech": 4,
    "m.eng": 4, "meng": 4, "m.com": 4, "mcom": 4, "mca": 4,
    "mba": 4, "m.b.a.": 4, "pgd": 4, "postgraduate": 4,
    "phd": 5, "ph.d.": 5, "ph.d": 5, "doctorate": 5, "doctoral": 5, "d.phil": 5,
    "博士": 5,
    "碩士": 4, "硕士": 4, "研究所": 4, "研究生": 4,
    "學士": 3, "学士": 3, "大學": 3, "大学": 3, "本科": 3,
    "專科": 2, "专科": 2,
    "高中": 1, "high school": 1,
}


def _detect_degree_level(degree_str: str) -> int:
    """Detect degree level using dictionary + substring heuristics."""
    d = degree_str.lower().strip()
    # Direct lookup
    if d in _DEGREE_LEVELS:
        return _DEGREE_LEVELS[d]
    # Substring search — check if any known key appears in the degree string
    for key, level in sorted(_DEGREE_LEVELS.items(), key=lambda x: -x[1]):
        if len(key) > 1 and key in d:
            return level
    # Heuristic keywords
    if any(w in d for w in ("bachelor", "undergraduate", "本科", "大學", "大学")):
        return 3
    if any(w in d for w in ("master", "graduate", "碩士", "硕士", "研究")):
        return 4
    if any(w in d for w in ("phd", "doctor", "博士")):
        return 5
    return 0

_DEGREE_WEIGHT = 0.5
_FIELD_WEIGHT = 0.5


class EducationMatcher(BaseScorer):
    dimension = "education"

    async def score(self, jd: ParsedJD, resume: ParsedResume) -> DimensionScore:
        evidence: list[str] = []

        # Degree level
        required_level = _detect_degree_level(jd.education.min_degree)
        candidate_level = 0
        candidate_degree_name = ""
        for edu in resume.education:
            lvl = _detect_degree_level(edu.degree)
            if lvl > candidate_level:
                candidate_level = lvl
                candidate_degree_name = edu.degree

        if required_level == 0:
            degree_score = 1.0
        elif candidate_level >= required_level:
            degree_score = 1.0
        elif candidate_level == required_level - 1:
            degree_score = 0.6
        else:
            degree_score = 0.2

        evidence.append(
            f"Degree: {candidate_degree_name or 'N/A'} (required: {jd.education.min_degree or 'any'})"
        )

        # Field relevance
        preferred_fields = [f.lower() for f in jd.education.preferred_fields]
        if not preferred_fields:
            field_score = 0.8  # No preference → neutral
        else:
            field_score = 0.0
            for edu in resume.education:
                edu_field = edu.field.lower()
                for pf in preferred_fields:
                    if pf in edu_field or edu_field in pf:
                        field_score = 1.0
                        evidence.append(f"Field match: {edu.field} ∈ {pf}")
                        break
                if field_score > 0:
                    break
            if field_score == 0 and resume.education:
                field_score = 0.3
                evidence.append(f"Field mismatch: {resume.education[0].field}")

        raw = degree_score * _DEGREE_WEIGHT + field_score * _FIELD_WEIGHT
        final_score = round(raw * 100, 1)

        # Seniority decay: education matters less as experience grows
        years = resume.total_years_experience or 0
        if years >= 12:
            edu_weight = 0.4    # 12+ years: career track record >> degree
        elif years >= 8:
            edu_weight = 0.55   # 8-12 years: education influence fading
        elif years >= 5:
            edu_weight = 0.7    # 5-8 years: still somewhat relevant
        else:
            edu_weight = 0.8    # < 5 years: education is a strong signal

        evidence.append(f"Weight decay: {edu_weight} (based on {years:.0f}y experience)")

        return DimensionScore(
            dimension=self.dimension,
            score=final_score,
            weight=edu_weight,
            details=f"Degree: {degree_score:.0%}, Field: {field_score:.0%}, Weight: {edu_weight}",
            evidence=evidence,
        )
