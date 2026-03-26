"""Domain entity: Evaluation result."""

from __future__ import annotations

import enum
from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.entities.dimension_score import DeterministicScores, LLMScores


class EvaluationStatus(str, enum.Enum):
    PENDING = "pending"
    PARSING = "parsing"
    SCORING_DETERMINISTIC = "scoring_deterministic"
    SCORING_LLM = "scoring_llm"
    FUSING = "fusing"
    COMPLETED = "completed"
    FAILED = "failed"


class Tier(str, enum.Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    F = "F"

    @classmethod
    def from_score(cls, score: float) -> Tier:
        if score >= 90:
            return cls.A
        if score >= 80:
            return cls.B
        if score >= 70:
            return cls.C
        if score >= 60:
            return cls.D
        return cls.F


class TokenUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0


class EvaluationResult(BaseModel):
    """Complete evaluation output for one JD×Resume pair."""

    id: str | None = None
    jd_id: str = ""
    resume_id: str = ""
    status: EvaluationStatus = EvaluationStatus.PENDING

    deterministic_scores: DeterministicScores | None = None
    llm_scores: LLMScores | None = None

    final_score: float = 0.0
    confidence: float = 0.0
    tier: Tier = Tier.F

    meta_summary: str = ""
    interview_questions: list[str] | dict = Field(default_factory=list)

    token_usage: TokenUsage = Field(default_factory=TokenUsage)
    processing_time_ms: int = 0

    created_at: datetime | None = None
    updated_at: datetime | None = None
