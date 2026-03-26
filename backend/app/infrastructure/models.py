"""SQLAlchemy ORM models."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database import Base

try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    Vector = None  # graceful fallback if pgvector not installed


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return uuid.uuid4().hex


class JobDescriptionModel(Base):
    __tablename__ = "job_descriptions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    title: Mapped[str] = mapped_column(String(500), default="")
    file_name: Mapped[str] = mapped_column(String(500), default="")
    raw_text: Mapped[str] = mapped_column(Text, default="")
    parsed_requirements: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    cache_key: Mapped[str] = mapped_column(String(64), default="", index=True)
    file_path: Mapped[str] = mapped_column(String(1000), default="")
    user_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class ResumeModel(Base):
    __tablename__ = "resumes"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    candidate_name: Mapped[str] = mapped_column(String(500), default="")
    raw_text: Mapped[str] = mapped_column(Text, default="")
    parsed_profile: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    file_hash: Mapped[str] = mapped_column(String(64), default="", index=True)
    file_path: Mapped[str] = mapped_column(String(1000), default="")
    user_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class EvaluationModel(Base):
    __tablename__ = "evaluations"
    __table_args__ = (UniqueConstraint("jd_id", "resume_id", name="uix_jd_resume"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    jd_id: Mapped[str] = mapped_column(String(32), index=True)
    resume_id: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(
        Enum("pending", "parsing", "scoring_deterministic", "scoring_llm", "fusing", "completed", "failed", name="eval_status"),
        default="pending",
    )
    deterministic_scores: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    llm_scores: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    final_score: Mapped[float] = mapped_column(Float, default=0.0)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    tier: Mapped[str] = mapped_column(String(5), default="D")
    meta_summary: Mapped[str] = mapped_column(Text, default="")
    interview_questions: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    token_usage: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    processing_time_ms: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str] = mapped_column(Text, default="")
    resume_file_name: Mapped[str] = mapped_column(String(500), default="")
    user_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class EvalConfigModel(Base):
    __tablename__ = "eval_configs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    dimension_weights: Mapped[dict] = mapped_column(JSONB, default=dict)
    deterministic_weight: Mapped[float] = mapped_column(Float, default=0.4)
    llm_weight: Mapped[float] = mapped_column(Float, default=0.6)
    model_name: Mapped[str] = mapped_column(String(100), default="gpt-4o")
    is_default: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


# ─────────────────────────────────────────────────────────────────
#  Calibration & Continuous Improvement Models
# ─────────────────────────────────────────────────────────────────


class EvalBenchmarkModel(Base):
    """Every evaluation from any source — our system, Gemini, Claude, human.

    Central table for cross-model comparison and calibration.
    """
    __tablename__ = "eval_benchmarks"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)

    # Link to JD/Resume (nullable — external analyses may not have IDs)
    jd_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    resume_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)

    # Source identification
    source: Mapped[str] = mapped_column(String(50), index=True)  # 'matchmaster', 'gemini', 'claude', 'human'
    source_version: Mapped[str] = mapped_column(String(100), default="")  # 'v2_graduated', 'gemini-2.5-pro'
    scoring_version_id: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # Scores
    overall_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    tier: Mapped[str] = mapped_column(String(5), default="")
    dimension_scores: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Qualitative analysis
    analysis_text: Mapped[str] = mapped_column(Text, default="")
    strengths: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # list[str]
    weaknesses: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # list[str]
    interview_questions: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # list[str]

    # Context
    candidate_name: Mapped[str] = mapped_column(String(500), default="")
    jd_title: Mapped[str] = mapped_column(String(500), default="")
    jd_file_name: Mapped[str] = mapped_column(String(500), default="")
    resume_file_name: Mapped[str] = mapped_column(String(500), default="")

    # Full raw data (for future re-analysis)
    raw_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    extra_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class EvalComparisonModel(Base):
    """Cross-model comparison record.

    Stores side-by-side analysis between two benchmarks (e.g., MatchMaster vs Gemini).
    """
    __tablename__ = "eval_comparisons"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)

    benchmark_a_id: Mapped[str] = mapped_column(String(32), index=True)
    benchmark_b_id: Mapped[str] = mapped_column(String(32), index=True)

    # Comparison content
    comparison_text: Mapped[str] = mapped_column(Text, default="")
    key_differences: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # list[str]

    # Judgment
    preferred_source: Mapped[str] = mapped_column(String(50), default="")
    accuracy_notes: Mapped[str] = mapped_column(Text, default="")

    # Who made the comparison
    compared_by: Mapped[str] = mapped_column(String(100), default="")  # 'user', 'gemini', 'claude'
    extra_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class ScoringVersionModel(Base):
    """Track scoring pipeline configuration over time.

    Every time we tune weights, thresholds, or prompt — snapshot it here.
    """
    __tablename__ = "scoring_versions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    version_name: Mapped[str] = mapped_column(String(100), unique=True)

    # Configuration snapshot
    deterministic_weights: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    llm_weights: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    fusion_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    prompt_hash: Mapped[str] = mapped_column(String(64), default="")

    # Description
    changes_description: Mapped[str] = mapped_column(Text, default="")

    # Active period
    active_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    active_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class CalibrationFeedbackModel(Base):
    """Human or cross-model feedback on evaluation accuracy.

    Used to track what we learned and what we changed.
    """
    __tablename__ = "calibration_feedback"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    benchmark_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    scoring_version_id: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # Human/expert assessment
    human_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    human_tier: Mapped[str] = mapped_column(String(5), default="")
    accuracy_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-5

    # Detailed feedback
    feedback_text: Mapped[str] = mapped_column(Text, default="")
    dimension_adjustments: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # What changed as a result
    action_taken: Mapped[str] = mapped_column(Text, default="")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class AuthenticitySignalModel(Base):
    """Track AI-generated resume detection signals for model training.

    Over time, verified outcomes help us distinguish genuine from fabricated patterns.
    """
    __tablename__ = "authenticity_signals"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    resume_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    benchmark_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)

    # Signal details
    signal_type: Mapped[str] = mapped_column(String(50))
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    evidence: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # list[str]

    # Verification (updated after human review)
    verified_outcome: Mapped[str] = mapped_column(String(20), default="unknown")
    verification_notes: Mapped[str] = mapped_column(Text, default="")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
