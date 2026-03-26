"""API v1: Job Description endpoints."""

from __future__ import annotations

import asyncio
import json
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.application.upload_jd import UploadJDUseCase
from app.config import settings
from app.infrastructure.database import get_db
from app.infrastructure.repositories.evaluation_repository import EvaluationRepository
from app.infrastructure.repositories.jd_repository import JDRepository

router = APIRouter(prefix="/jd", tags=["Job Description"])

_MAX_SIZE = settings.max_file_size_mb * 1024 * 1024


@router.post("")
async def upload_jd(file: UploadFile, db: AsyncSession = Depends(get_db)):
    """Upload and parse a Job Description document (PDF/DOCX/TXT)."""
    if not file.filename:
        raise HTTPException(400, "Filename is required")

    content = await file.read()
    if len(content) > _MAX_SIZE:
        raise HTTPException(413, f"File too large (max {settings.max_file_size_mb}MB)")

    use_case = UploadJDUseCase(db)
    result = await use_case.execute_async(file.filename, content)
    return result


@router.get("/{jd_id}/stream")
async def stream_jd(jd_id: str, db: AsyncSession = Depends(get_db)):
    """SSE stream for JD parsing progress."""
    repo = JDRepository(db)

    async def event_generator() -> AsyncGenerator[dict, None]:
        for _ in range(120):  # max ~120s
            # Use select() with populate_existing to bypass stale identity map.
            # The background LLM task commits in a separate session; session.get()
            # would keep returning the cached "parsing" state forever.
            from app.infrastructure.models import JobDescriptionModel

            result = await db.execute(
                select(JobDescriptionModel)
                .where(JobDescriptionModel.id == jd_id)
                .execution_options(populate_existing=True)
            )
            jd = result.scalar_one_or_none()
            if not jd:
                yield {"event": "error", "data": json.dumps({"error": "not_found"})}
                return

            if jd.parsed_requirements is not None:
                # Check for error sentinel
                if isinstance(jd.parsed_requirements, dict) and jd.parsed_requirements.get("error"):
                    yield {"event": "failed", "data": json.dumps({
                        "status": "failed",
                        "error": jd.parsed_requirements["error"],
                    })}
                else:
                    yield {"event": "complete", "data": json.dumps({
                        "status": "completed",
                        "id": jd.id,
                        "title": jd.title,
                        "file_name": jd.file_name,
                        "parsed_requirements": jd.parsed_requirements,
                        "created_at": jd.created_at.isoformat() if jd.created_at else None,
                    }, ensure_ascii=False)}
                return

            yield {"event": "progress", "data": json.dumps({"status": "parsing"})}
            await asyncio.sleep(1)

    return EventSourceResponse(event_generator())


@router.get("/{jd_id}")
async def get_jd(jd_id: str, db: AsyncSession = Depends(get_db)):
    """Get a parsed JD by ID."""
    repo = JDRepository(db)
    jd = await repo.get_by_id(jd_id)
    if not jd:
        raise HTTPException(404, "JD not found")
    # Derive status from parsed_requirements: null = still parsing
    if jd.parsed_requirements is None:
        status = "parsing"
    elif isinstance(jd.parsed_requirements, dict) and jd.parsed_requirements.get("error"):
        status = "failed"
    else:
        status = "completed"
    return {
        "id": jd.id,
        "title": jd.title,
        "file_name": jd.file_name,
        "status": status,
        "parsed_requirements": jd.parsed_requirements,
        "created_at": jd.created_at.isoformat() if jd.created_at else None,
    }


@router.get("")
async def list_jds(
    limit: int = 50, offset: int = 0, db: AsyncSession = Depends(get_db)
):
    """List all uploaded JDs with eval counts."""
    repo = JDRepository(db)
    eval_repo = EvaluationRepository(db)
    jds = await repo.list_all(limit=limit, offset=offset)
    result = []
    for jd in jds:
        count = await eval_repo.count_by_jd(jd.id)
        last_eval_at = await eval_repo.latest_created_at_by_jd(jd.id)
        result.append({
            "id": jd.id,
            "title": jd.title,
            "file_name": jd.file_name,
            "status": "completed" if jd.parsed_requirements is not None else "parsing",
            "eval_count": count,
            "created_at": jd.created_at.isoformat() if jd.created_at else None,
            "last_evaluated_at": last_eval_at.isoformat() if last_eval_at else None,
        })
    return result


@router.delete("/{jd_id}")
async def delete_jd(jd_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a JD and its associated evaluations."""
    from app.infrastructure.repositories.evaluation_repository import EvaluationRepository

    eval_repo = EvaluationRepository(db)
    # Delete all evaluations under this JD first
    evals = await eval_repo.list_by_jd(jd_id)
    for ev in evals:
        await eval_repo.delete(ev.id)

    repo = JDRepository(db)
    deleted = await repo.delete(jd_id)
    if not deleted:
        raise HTTPException(404, "JD not found")
    return {"ok": True}
