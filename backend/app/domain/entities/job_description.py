"""Domain entity: Job Description."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SkillRequirement(BaseModel):
    name: str
    level: str = ""  # e.g. "proficient", "expert"
    is_must_have: bool = True
    years: float | None = None


class ExperienceRequirement(BaseModel):
    min_years: float = 0
    preferred_years: float | None = None
    industries: list[str] = Field(default_factory=list)
    description: str = ""


class EducationRequirement(BaseModel):
    min_degree: str = ""  # e.g. "bachelor", "master", "phd"
    preferred_fields: list[str] = Field(default_factory=list)
    required: bool = False


class ParsedJD(BaseModel):
    """Structured output from LLM JD extraction."""

    title: str = ""
    company: str = ""
    department: str = ""
    location: str = ""
    employment_type: str = ""  # full-time, part-time, contract
    summary: str = ""

    must_have_skills: list[SkillRequirement] = Field(default_factory=list)
    nice_to_have_skills: list[SkillRequirement] = Field(default_factory=list)

    experience: ExperienceRequirement = Field(default_factory=ExperienceRequirement)
    education: EducationRequirement = Field(default_factory=EducationRequirement)

    responsibilities: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    language_requirements: list[str] = Field(default_factory=list)
    soft_skill_keywords: list[str] = Field(default_factory=list)
