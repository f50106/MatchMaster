"""API v1: Calibration & Benchmark endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import get_db
from app.infrastructure.repositories.benchmark_repository import BenchmarkRepository

router = APIRouter(prefix="/calibration", tags=["Calibration"])


# ── Request schemas ──


class BenchmarkCreate(BaseModel):
    jd_id: str | None = None
    resume_id: str | None = None
    source: str  # 'matchmaster', 'gemini', 'claude', 'human'
    source_version: str = ""
    overall_score: float | None = None
    tier: str = ""
    dimension_scores: dict | None = None
    analysis_text: str = ""
    strengths: list[str] | None = None
    weaknesses: list[str] | None = None
    interview_questions: list[str] | None = None
    candidate_name: str = ""
    jd_title: str = ""
    jd_file_name: str = ""
    resume_file_name: str = ""
    raw_data: dict | None = None
    extra_data: dict | None = None


class ComparisonCreate(BaseModel):
    benchmark_a_id: str
    benchmark_b_id: str
    comparison_text: str = ""
    key_differences: list[str] | None = None
    preferred_source: str = ""
    accuracy_notes: str = ""
    compared_by: str = ""
    extra_data: dict | None = None


class ScoringVersionCreate(BaseModel):
    version_name: str
    deterministic_weights: dict | None = None
    llm_weights: dict | None = None
    fusion_config: dict | None = None
    prompt_hash: str = ""
    changes_description: str = ""


class FeedbackCreate(BaseModel):
    benchmark_id: str | None = None
    scoring_version_id: str | None = None
    human_score: float | None = None
    human_tier: str = ""
    accuracy_rating: int | None = Field(None, ge=1, le=5)
    feedback_text: str = ""
    dimension_adjustments: dict | None = None
    action_taken: str = ""


class SignalCreate(BaseModel):
    resume_id: str | None = None
    benchmark_id: str | None = None
    signal_type: str
    confidence: float = 0.0
    evidence: list[str] | None = None
    verified_outcome: str = "unknown"
    verification_notes: str = ""


# ── Helpers ──


def _model_to_dict(obj) -> dict:
    """Convert SQLAlchemy model to dict, excluding internal attrs."""
    return {
        c.name: getattr(obj, c.name)
        for c in obj.__table__.columns
    }


# ── Benchmarks ──


@router.post("/benchmarks")
async def create_benchmark(body: BenchmarkCreate, db: AsyncSession = Depends(get_db)):
    """Store an evaluation from any source (MatchMaster, Gemini, human, etc.)."""
    repo = BenchmarkRepository(db)
    obj = await repo.create_benchmark(**body.model_dump())
    return _model_to_dict(obj)


@router.get("/benchmarks")
async def list_benchmarks(
    jd_id: str | None = None,
    resume_id: str | None = None,
    source: str | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """List benchmarks, optionally filtered by JD, resume, or source."""
    repo = BenchmarkRepository(db)
    if jd_id and resume_id:
        items = await repo.list_benchmarks_by_resume(jd_id, resume_id)
    elif source:
        items = await repo.list_benchmarks_by_source(source, limit)
    else:
        items = await repo.list_all_benchmarks(limit)
    return [_model_to_dict(i) for i in items]


@router.get("/benchmarks/{benchmark_id}")
async def get_benchmark(benchmark_id: str, db: AsyncSession = Depends(get_db)):
    """Get a single benchmark by ID."""
    repo = BenchmarkRepository(db)
    obj = await repo.get_benchmark(benchmark_id)
    if not obj:
        raise HTTPException(404, "Benchmark not found")
    return _model_to_dict(obj)


# ── Comparisons ──


@router.post("/comparisons")
async def create_comparison(body: ComparisonCreate, db: AsyncSession = Depends(get_db)):
    """Create a cross-model comparison record."""
    repo = BenchmarkRepository(db)
    obj = await repo.create_comparison(**body.model_dump())
    return _model_to_dict(obj)


@router.get("/comparisons")
async def list_comparisons(limit: int = 50, db: AsyncSession = Depends(get_db)):
    """List all comparison records."""
    repo = BenchmarkRepository(db)
    items = await repo.list_comparisons(limit)
    return [_model_to_dict(i) for i in items]


# ── Scoring Versions ──


@router.post("/scoring-versions")
async def create_scoring_version(
    body: ScoringVersionCreate, db: AsyncSession = Depends(get_db)
):
    """Snapshot current scoring pipeline configuration."""
    repo = BenchmarkRepository(db)
    obj = await repo.create_scoring_version(**body.model_dump())
    return _model_to_dict(obj)


@router.get("/scoring-versions")
async def list_scoring_versions(db: AsyncSession = Depends(get_db)):
    """List all scoring versions."""
    repo = BenchmarkRepository(db)
    items = await repo.list_scoring_versions()
    return [_model_to_dict(i) for i in items]


@router.get("/scoring-versions/active")
async def get_active_version(db: AsyncSession = Depends(get_db)):
    """Get the currently active scoring version."""
    repo = BenchmarkRepository(db)
    obj = await repo.get_active_version()
    if not obj:
        return None
    return _model_to_dict(obj)


# ── Calibration Feedback ──


@router.post("/feedback")
async def create_feedback(body: FeedbackCreate, db: AsyncSession = Depends(get_db)):
    """Submit calibration feedback on an evaluation."""
    repo = BenchmarkRepository(db)
    obj = await repo.create_feedback(**body.model_dump())
    return _model_to_dict(obj)


@router.get("/feedback")
async def list_feedback(limit: int = 50, db: AsyncSession = Depends(get_db)):
    """List calibration feedback."""
    repo = BenchmarkRepository(db)
    items = await repo.list_feedback(limit)
    return [_model_to_dict(i) for i in items]


# ── Authenticity Signals ──


@router.post("/signals")
async def create_signal(body: SignalCreate, db: AsyncSession = Depends(get_db)):
    """Record an AI resume authenticity signal."""
    repo = BenchmarkRepository(db)
    obj = await repo.create_signal(**body.model_dump())
    return _model_to_dict(obj)


@router.get("/signals/{resume_id}")
async def list_signals_by_resume(resume_id: str, db: AsyncSession = Depends(get_db)):
    """List authenticity signals for a resume."""
    repo = BenchmarkRepository(db)
    items = await repo.list_signals_by_resume(resume_id)
    return [_model_to_dict(i) for i in items]


# ── Analytics ──


@router.get("/drift")
async def score_drift(db: AsyncSession = Depends(get_db)):
    """Aggregate avg scores per source — detect score drift across models."""
    repo = BenchmarkRepository(db)
    return await repo.score_drift_by_source()
