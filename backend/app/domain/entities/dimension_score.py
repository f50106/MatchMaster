"""Domain entity: Dimension Score (individual scoring dimension)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class DimensionScore(BaseModel):
    """A single scoring dimension result."""

    dimension: str  # e.g. "technical_skills", "work_experience"
    score: float = 0.0  # 0-100
    confidence: float = 1.0  # 0-1
    weight: float = 1.0
    details: str = ""
    evidence: list[str] = Field(default_factory=list)


class DeterministicScores(BaseModel):
    """All Stage 1 deterministic scores."""

    skill_match: DimensionScore = Field(
        default_factory=lambda: DimensionScore(dimension="skill_match")
    )
    experience: DimensionScore = Field(
        default_factory=lambda: DimensionScore(dimension="experience")
    )
    education: DimensionScore = Field(
        default_factory=lambda: DimensionScore(dimension="education")
    )
    keyword_overlap: DimensionScore = Field(
        default_factory=lambda: DimensionScore(dimension="keyword_overlap")
    )
    red_flags: DimensionScore = Field(
        default_factory=lambda: DimensionScore(dimension="red_flags")
    )
    depth_analysis: DimensionScore = Field(
        default_factory=lambda: DimensionScore(dimension="depth_analysis")
    )
    career_progression: DimensionScore = Field(
        default_factory=lambda: DimensionScore(dimension="career_progression")
    )

    @property
    def all_dims(self) -> list[DimensionScore]:
        return [
            self.skill_match, self.experience, self.depth_analysis,
            self.red_flags, self.education, self.career_progression,
            self.keyword_overlap,
        ]

    @property
    def weighted_average(self) -> float:
        dims = self.all_dims
        total_weight = sum(d.weight for d in dims)
        if total_weight == 0:
            return 0.0
        return sum(d.score * d.weight for d in dims) / total_weight


class LLMDimensionScore(BaseModel):
    """Single dimension from LLM evaluation."""

    dimension: str
    score: float = 0.0
    reasoning: str = ""
    evidence: list[str] = Field(default_factory=list)


class LLMScores(BaseModel):
    """All Stage 2 LLM evaluation scores."""

    technical_skills: LLMDimensionScore = Field(
        default_factory=lambda: LLMDimensionScore(dimension="technical_skills")
    )
    work_experience: LLMDimensionScore = Field(
        default_factory=lambda: LLMDimensionScore(dimension="work_experience")
    )
    education: LLMDimensionScore = Field(
        default_factory=lambda: LLMDimensionScore(dimension="education")
    )
    career_trajectory: LLMDimensionScore = Field(
        default_factory=lambda: LLMDimensionScore(dimension="career_trajectory")
    )
    red_flags: LLMDimensionScore = Field(
        default_factory=lambda: LLMDimensionScore(dimension="red_flags")
    )
    soft_skills: LLMDimensionScore = Field(
        default_factory=lambda: LLMDimensionScore(dimension="soft_skills")
    )
    language_fit: LLMDimensionScore = Field(
        default_factory=lambda: LLMDimensionScore(dimension="language_fit")
    )

    overall_score: float = 0.0
    meta_summary: str = ""
    meta_summary_en: str = ""
    meta_summary_zh: str = ""
    interview_questions: list[str] | dict = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    strengths_en: list[str] = Field(default_factory=list)
    strengths_zh: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    weaknesses_en: list[str] = Field(default_factory=list)
    weaknesses_zh: list[str] = Field(default_factory=list)

    # Weighted importance per dimension
    _DIM_WEIGHTS: dict[str, float] = {
        "technical_skills": 1.5,
        "work_experience": 2.0,
        "education": 0.6,
        "career_trajectory": 1.5,
        "red_flags": 0.8,
        "soft_skills": 1.0,
        "language_fit": 0.4,
    }

    @property
    def all_dims(self) -> list[LLMDimensionScore]:
        return [
            self.technical_skills, self.work_experience, self.education,
            self.career_trajectory, self.red_flags, self.soft_skills,
            self.language_fit,
        ]

    @property
    def weighted_average(self) -> float:
        dims = self.all_dims
        total_w = 0.0
        weighted_sum = 0.0
        for d in dims:
            w = self._DIM_WEIGHTS.get(d.dimension, 1.0)
            weighted_sum += d.score * w
            total_w += w
        return weighted_sum / total_w if total_w else 0.0
