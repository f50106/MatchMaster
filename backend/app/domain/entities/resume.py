"""Domain entity: Resume / Candidate Profile."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


def _coerce_str(v: object) -> str:
    """Coerce None or non-str values to empty string."""
    if v is None:
        return ""
    return str(v)


def _coerce_opt_int(v: object) -> int | None:
    """Coerce flexible input to int or None."""
    if v is None or v == "":
        return None
    try:
        return int(v)
    except (ValueError, TypeError):
        return None


class WorkExperience(BaseModel):
    company: str = ""
    title: str = ""
    start_date: str = ""  # YYYY-MM or approximate
    end_date: str = ""  # YYYY-MM, "present", or ""
    duration_months: int | None = None
    industry: str = ""
    description: str = ""
    skills_used: list[str] = Field(default_factory=list)

    @field_validator("company", "title", "start_date", "end_date", "industry", "description", mode="before")
    @classmethod
    def _str(cls, v: object) -> str:
        return _coerce_str(v)

    @field_validator("duration_months", mode="before")
    @classmethod
    def _int(cls, v: object) -> int | None:
        return _coerce_opt_int(v)


class Education(BaseModel):
    institution: str = ""
    degree: str = ""  # "bachelor", "master", "phd", "associate", "diploma"
    field: str = ""
    graduation_year: int | None = None
    gpa: str = ""

    @field_validator("institution", "degree", "field", "gpa", mode="before")
    @classmethod
    def _str(cls, v: object) -> str:
        return _coerce_str(v)

    @field_validator("graduation_year", mode="before")
    @classmethod
    def _int(cls, v: object) -> int | None:
        return _coerce_opt_int(v)


class Certification(BaseModel):
    name: str = ""
    issuer: str = ""
    year: int | None = None

    @field_validator("name", "issuer", mode="before")
    @classmethod
    def _str(cls, v: object) -> str:
        return _coerce_str(v)

    @field_validator("year", mode="before")
    @classmethod
    def _int(cls, v: object) -> int | None:
        return _coerce_opt_int(v)


class ParsedResume(BaseModel):
    """Structured output from LLM resume extraction."""

    candidate_name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    summary: str = ""

    skills: list[str] = Field(default_factory=list)
    work_experiences: list[WorkExperience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    certifications: list[Certification] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    total_years_experience: float | None = None
    current_title: str = ""
    current_company: str = ""
