"""Use case: Batch evaluate multiple resumes against a JD."""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.run_evaluation import RunEvaluationUseCase
from app.infrastructure.database import async_session_factory

logger = logging.getLogger(__name__)


class BatchEvaluationUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def execute(
        self,
        jd_id: str,
        files: list[tuple[str, bytes]],  # (filename, content)
        concurrency: int = 3,
    ) -> dict:
        """Evaluate multiple resumes concurrently with semaphore-limited parallelism."""
        results: list[dict] = []
        errors: list[dict] = []
        sem = asyncio.Semaphore(concurrency)

        async def _eval_one(filename: str, content: bytes) -> None:
            async with sem:
                try:
                    async with async_session_factory() as session:
                        use_case = RunEvaluationUseCase(session)
                        # execute_async returns pending eval immediately; pipeline
                        # runs in background so all files are queued quickly.
                        result = await use_case.execute_async(jd_id, filename, content)
                        results.append(result)
                except Exception as e:
                    logger.exception("Batch eval failed for %s", filename)
                    errors.append({"filename": filename, "error": str(e)})

        await asyncio.gather(*[_eval_one(fn, ct) for fn, ct in files])

        # Sort by final score descending
        results.sort(key=lambda r: r.get("final_score", 0), reverse=True)

        return {
            "jd_id": jd_id,
            "total": len(files),
            "completed": len(results),
            "failed": len(errors),
            "results": results,
            "errors": errors,
        }
