"""API v1: Stats / cost tracking endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import get_db
from app.infrastructure.models import EvaluationModel

router = APIRouter(prefix="/stats", tags=["Stats"])


@router.get("/cost")
async def get_cost_stats(db: AsyncSession = Depends(get_db)):
    """Get aggregated token usage and cost statistics."""
    stmt = select(
        func.count(EvaluationModel.id).label("total_evaluations"),
        func.avg(EvaluationModel.final_score).label("avg_score"),
        func.avg(EvaluationModel.processing_time_ms).label("avg_processing_ms"),
    ).where(EvaluationModel.status == "completed")

    result = await db.execute(stmt)
    row = result.one()

    # Aggregate token usage from JSONB
    token_stmt = select(EvaluationModel.token_usage).where(
        EvaluationModel.status == "completed",
        EvaluationModel.token_usage.isnot(None),
    )
    token_result = await db.execute(token_stmt)
    usages = token_result.scalars().all()

    total_prompt = sum(u.get("prompt_tokens", 0) for u in usages if u)
    total_completion = sum(u.get("completion_tokens", 0) for u in usages if u)
    total_cost = sum(u.get("estimated_cost_usd", 0) for u in usages if u)

    return {
        "total_evaluations": row.total_evaluations or 0,
        "avg_score": round(row.avg_score or 0, 1),
        "avg_processing_ms": int(row.avg_processing_ms or 0),
        "total_prompt_tokens": total_prompt,
        "total_completion_tokens": total_completion,
        "total_tokens": total_prompt + total_completion,
        "total_cost_usd": round(total_cost, 4),
    }
