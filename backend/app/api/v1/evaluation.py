"""API v1: Evaluation endpoints."""

from __future__ import annotations

import asyncio
import json
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.application.batch_evaluation import BatchEvaluationUseCase
from app.application.run_evaluation import RunEvaluationUseCase
from app.config import settings
from app.infrastructure.database import get_db
from app.infrastructure.repositories.evaluation_repository import EvaluationRepository

router = APIRouter(tags=["Evaluation"])

_MAX_SIZE = settings.max_file_size_mb * 1024 * 1024


@router.post("/jd/{jd_id}/evaluate")
async def evaluate_resume(
    jd_id: str, file: UploadFile, db: AsyncSession = Depends(get_db)
):
    """Upload a resume and evaluate it against a JD."""
    if not file.filename:
        raise HTTPException(400, "Filename is required")

    content = await file.read()
    if len(content) > _MAX_SIZE:
        raise HTTPException(413, f"File too large (max {settings.max_file_size_mb}MB)")

    use_case = RunEvaluationUseCase(db)
    result = await use_case.execute_async(jd_id, file.filename, content)
    return result


@router.post("/jd/{jd_id}/evaluate/batch")
async def batch_evaluate(
    jd_id: str, files: list[UploadFile], db: AsyncSession = Depends(get_db)
):
    """Batch evaluate multiple resumes against a JD."""
    if not files:
        raise HTTPException(400, "At least one file is required")

    file_data: list[tuple[str, bytes]] = []
    for f in files:
        if not f.filename:
            continue
        content = await f.read()
        if len(content) > _MAX_SIZE:
            raise HTTPException(413, f"File {f.filename} too large")
        file_data.append((f.filename, content))

    use_case = BatchEvaluationUseCase(db)
    result = await use_case.execute(jd_id, file_data)
    return result


@router.get("/evaluations/{eval_id}")
async def get_evaluation(eval_id: str, db: AsyncSession = Depends(get_db)):
    """Get a single evaluation result."""
    repo = EvaluationRepository(db)
    ev = await repo.get_by_id(eval_id)
    if not ev:
        raise HTTPException(404, "Evaluation not found")
    return {
        "id": ev.id,
        "jd_id": ev.jd_id,
        "resume_id": ev.resume_id,
        "status": ev.status,
        "final_score": ev.final_score,
        "confidence": ev.confidence,
        "tier": ev.tier,
        "meta_summary": ev.meta_summary,
        "interview_questions": ev.interview_questions,
        "deterministic_scores": ev.deterministic_scores,
        "llm_scores": ev.llm_scores,
        "token_usage": ev.token_usage,
        "processing_time_ms": ev.processing_time_ms,
        "error_message": ev.error_message or "",
        "resume_file_name": ev.resume_file_name or "",
        "created_at": ev.created_at.isoformat() if ev.created_at else None,
    }


@router.get("/evaluations/{eval_id}/stream")
async def stream_evaluation(eval_id: str, db: AsyncSession = Depends(get_db)):
    """SSE stream for evaluation progress."""
    repo = EvaluationRepository(db)

    async def event_generator() -> AsyncGenerator[dict, None]:
        for _ in range(120):  # Max 120 polls (~120s)
            # Use select() with populate_existing to bypass stale identity map.
            # The background pipeline commits in a separate session; session.get()
            # would keep returning the cached "parsing" state forever.
            from app.infrastructure.models import EvaluationModel

            result = await db.execute(
                select(EvaluationModel)
                .where(EvaluationModel.id == eval_id)
                .execution_options(populate_existing=True)
            )
            ev = result.scalar_one_or_none()
            if not ev:
                yield {"event": "error", "data": json.dumps({"error": "not_found"})}
                return

            data: dict = {"status": ev.status}

            if ev.status == "completed":
                data.update({
                    "final_score": ev.final_score,
                    "tier": ev.tier,
                    "confidence": ev.confidence,
                    "meta_summary": ev.meta_summary,
                    "processing_time_ms": ev.processing_time_ms,
                    "deterministic_scores": ev.deterministic_scores,
                    "llm_scores": ev.llm_scores,
                    "resume_file_name": ev.resume_file_name or "",
                    "created_at": ev.created_at.isoformat() if ev.created_at else None,
                })
                yield {"event": "complete", "data": json.dumps(data, ensure_ascii=False)}
                return

            if ev.status == "failed":
                data["error_message"] = ev.error_message or ""
                yield {"event": "failed", "data": json.dumps(data, ensure_ascii=False)}
                return

            yield {"event": "progress", "data": json.dumps(data, ensure_ascii=False)}
            await asyncio.sleep(1)

    return EventSourceResponse(event_generator())


@router.delete("/evaluations/{eval_id}")
async def delete_evaluation(eval_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a single evaluation."""
    repo = EvaluationRepository(db)
    deleted = await repo.delete(eval_id)
    if not deleted:
        raise HTTPException(404, "Evaluation not found")
    return {"ok": True}


@router.get("/jd/{jd_id}/evaluations")
async def list_evaluations(
    jd_id: str,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """Get ranked evaluations for a JD."""
    repo = EvaluationRepository(db)
    evals = await repo.list_by_jd(jd_id, limit=limit, offset=offset)
    return [
        {
            "id": ev.id,
            "resume_id": ev.resume_id,
            "status": ev.status,
            "final_score": ev.final_score,
            "confidence": ev.confidence,
            "tier": ev.tier,
            "meta_summary": ev.meta_summary,
            "processing_time_ms": ev.processing_time_ms,
            "error_message": ev.error_message or "",
            "resume_file_name": ev.resume_file_name or "",
            "created_at": ev.created_at.isoformat() if ev.created_at else None,
        }
        for ev in evals
    ]


@router.get("/jd/{jd_id}/evaluations/compare")
async def compare_evaluations(
    jd_id: str,
    ids: str = "",  # comma-separated eval IDs
    db: AsyncSession = Depends(get_db),
):
    """Compare multiple evaluations side by side."""
    if not ids:
        raise HTTPException(400, "Provide comma-separated evaluation IDs")

    eval_ids = [eid.strip() for eid in ids.split(",") if eid.strip()]
    repo = EvaluationRepository(db)
    results = []
    for eid in eval_ids:
        ev = await repo.get_by_id(eid)
        if ev and ev.jd_id == jd_id:
            results.append({
                "id": ev.id,
                "resume_id": ev.resume_id,
                "final_score": ev.final_score,
                "confidence": ev.confidence,
                "tier": ev.tier,
                "deterministic_scores": ev.deterministic_scores,
                "llm_scores": ev.llm_scores,
                "meta_summary": ev.meta_summary,
                "interview_questions": ev.interview_questions,
            })

    return {"jd_id": jd_id, "comparisons": results}
