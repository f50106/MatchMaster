"""Use case: Run single resume evaluation against a JD."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.evaluation import EvaluationStatus
from app.domain.services.evaluation_orchestrator import EvaluationOrchestrator
from app.infrastructure.database import async_session_factory
from app.infrastructure.parsers.docx_parser import DocxParser
from app.infrastructure.parsers.pdf_parser import PDFParser
from app.infrastructure.repositories.benchmark_repository import BenchmarkRepository
from app.infrastructure.repositories.evaluation_repository import EvaluationRepository
from app.infrastructure.repositories.jd_repository import JDRepository
from app.infrastructure.repositories.resume_repository import ResumeRepository
from app.infrastructure.storage.local_storage import LocalStorage

logger = logging.getLogger(__name__)


class RunEvaluationUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._jd_repo = JDRepository(session)
        self._resume_repo = ResumeRepository(session)
        self._eval_repo = EvaluationRepository(session)
        self._storage = LocalStorage()
        self._orchestrator = EvaluationOrchestrator()
        self._parsers = [PDFParser(), DocxParser()]

    async def execute(
        self, jd_id: str, filename: str, file_content: bytes
    ) -> dict:
        """Upload resume → parse → run 3-stage pipeline → store result."""
        # 1. Get JD
        jd_model = await self._jd_repo.get_by_id(jd_id)
        if not jd_model:
            raise ValueError(f"JD not found: {jd_id}")

        # 2. Save resume file
        file_path = await self._storage.save(filename, file_content)
        file_hash = hashlib.sha256(file_content).hexdigest()

        # 3. Parse resume
        raw_text = ""
        for parser in self._parsers:
            if parser.supports(filename):
                result = await parser.parse(file_path)
                raw_text = result.raw_text
                break
        else:
            raw_text = file_content.decode("utf-8", errors="replace")

        # 4. Always create a fresh resume record per upload so that the same
        # content uploaded under a different filename (or re-uploaded) still
        # generates a new evaluation row without hitting the (jd_id, resume_id)
        # unique constraint.  The file_hash is still passed for reference /
        # future de-dup queries, but we no longer reuse the resume_id here.
        resume_model = await self._resume_repo.create(
            raw_text=raw_text,
            file_hash=file_hash,
            file_path=file_path,
        )

        # 5. Always create a new evaluation record so pipeline always runs.
        eval_model = await self._eval_repo.create(
            jd_id=jd_id,
            resume_id=resume_model.id,
            status="parsing",
        )

        # 7. Run evaluation pipeline
        try:
            result = await self._orchestrator.evaluate(
                jd_raw_text=jd_model.raw_text,
                resume_raw_text=raw_text,
            )

            # 8. Update resume with parsed profile
            if result.llm_scores:
                await self._resume_repo.update(
                    resume_model.id,
                    candidate_name=result.meta_summary[:100] if result.meta_summary else "",
                )

            # 9. Save evaluation results
            await self._eval_repo.update(
                eval_model.id,
                status="completed",
                deterministic_scores=result.deterministic_scores.model_dump() if result.deterministic_scores else None,
                llm_scores=result.llm_scores.model_dump() if result.llm_scores else None,
                final_score=result.final_score,
                confidence=result.confidence,
                tier=result.tier.value,
                meta_summary=result.meta_summary,
                interview_questions=result.interview_questions,
                token_usage=result.token_usage.model_dump(),
                processing_time_ms=result.processing_time_ms,
            )

            eval_model = await self._eval_repo.get_by_id(eval_model.id)

        except Exception as e:
            logger.exception("Evaluation failed for %s", eval_model.id)
            await self._eval_repo.update(
                eval_model.id,
                status="failed",
                error_message=str(e),
            )
            raise

        return self._to_response(eval_model)

    # ------------------------------------------------------------------ async

    async def execute_async(self, jd_id: str, filename: str, file_content: bytes) -> dict:
        """Parse & persist immediately, fire orchestration in background.

        Returns a pending EvaluationDetail within ~200 ms so the UI can show a
        "Analyzing…" row straight away and subscribe to the SSE progress stream.
        """
        eval_model, jd_raw_text, resume_id, resume_raw_text, jd_meta = await self._prepare(
            jd_id, filename, file_content
        )
        asyncio.create_task(
            self._run_pipeline_bg(
                eval_model.id, jd_raw_text, resume_id, resume_raw_text,
                jd_id=jd_id, jd_title=jd_meta["title"],
                jd_file_name=jd_meta["file_name"],
                resume_file_name=filename,
            )
        )
        return self._to_response(eval_model)

    async def _prepare(
        self, jd_id: str, filename: str, file_content: bytes
    ) -> tuple:
        """Steps 1-5: parse file, persist resume + pending eval, return tuple."""
        jd_model = await self._jd_repo.get_by_id(jd_id)
        if not jd_model:
            raise ValueError(f"JD not found: {jd_id}")

        file_path = await self._storage.save(filename, file_content)
        file_hash = hashlib.sha256(file_content).hexdigest()

        raw_text = ""
        for parser in self._parsers:
            if parser.supports(filename):
                result = await parser.parse(file_path)
                raw_text = result.raw_text
                break
        else:
            raw_text = file_content.decode("utf-8", errors="replace")

        resume_model = await self._resume_repo.create(
            raw_text=raw_text,
            file_hash=file_hash,
            file_path=file_path,
        )

        # Use filename (without ext) as placeholder summary so the pending row
        # shows a meaningful label in the UI before analysis completes.
        display_name = os.path.splitext(filename)[0]
        eval_model = await self._eval_repo.create(
            jd_id=jd_id,
            resume_id=resume_model.id,
            status="parsing",
            meta_summary=display_name,
            resume_file_name=filename,
        )
        jd_meta = {"title": jd_model.title, "file_name": jd_model.file_name}
        return eval_model, jd_model.raw_text, resume_model.id, raw_text, jd_meta

    async def _run_pipeline_bg(
        self,
        eval_id: str,
        jd_raw_text: str,
        resume_id: str,
        resume_raw_text: str,
        *,
        jd_id: str = "",
        jd_title: str = "",
        jd_file_name: str = "",
        resume_file_name: str = "",
    ) -> None:
        """Background coroutine: runs orchestration with its own DB session."""
        async with async_session_factory() as session:
            eval_repo = EvaluationRepository(session)
            resume_repo = ResumeRepository(session)
            benchmark_repo = BenchmarkRepository(session)
            try:
                result = await self._orchestrator.evaluate(
                    jd_raw_text=jd_raw_text,
                    resume_raw_text=resume_raw_text,
                )
                if result.meta_summary:
                    await resume_repo.update(
                        resume_id, candidate_name=result.meta_summary[:100]
                    )
                await eval_repo.update(
                    eval_id,
                    status="completed",
                    deterministic_scores=(
                        result.deterministic_scores.model_dump()
                        if result.deterministic_scores
                        else None
                    ),
                    llm_scores=(
                        result.llm_scores.model_dump() if result.llm_scores else None
                    ),
                    final_score=result.final_score,
                    confidence=result.confidence,
                    tier=result.tier.value,
                    meta_summary=result.meta_summary,
                    interview_questions=result.interview_questions,
                    token_usage=result.token_usage.model_dump(),
                    processing_time_ms=result.processing_time_ms,
                )

                # Auto-save to calibration benchmarks
                try:
                    await benchmark_repo.create_benchmark(
                        jd_id=jd_id,
                        resume_id=resume_id,
                        source="matchmaster",
                        source_version="v2_graduated",
                        overall_score=result.final_score,
                        tier=result.tier.value,
                        dimension_scores={
                            "deterministic": (
                                result.deterministic_scores.model_dump()
                                if result.deterministic_scores else None
                            ),
                            "llm": (
                                result.llm_scores.model_dump()
                                if result.llm_scores else None
                            ),
                        },
                        analysis_text=result.meta_summary or "",
                        interview_questions=result.interview_questions,
                        candidate_name=result.meta_summary[:100] if result.meta_summary else "",
                        jd_title=jd_title,
                        jd_file_name=jd_file_name,
                        resume_file_name=resume_file_name,
                    )
                except Exception:
                    logger.warning("Failed to save benchmark for eval %s", eval_id, exc_info=True)

            except Exception as e:
                logger.exception("Background pipeline failed for eval %s", eval_id)
                await eval_repo.update(eval_id, status="failed", error_message=str(e))

    @staticmethod
    def _to_response(model) -> dict:
        return {
            "id": model.id,
            "jd_id": model.jd_id,
            "resume_id": model.resume_id,
            "status": model.status,
            "final_score": model.final_score,
            "confidence": model.confidence,
            "tier": model.tier,
            "meta_summary": model.meta_summary,
            "interview_questions": model.interview_questions,
            "deterministic_scores": model.deterministic_scores,
            "llm_scores": model.llm_scores,
            "token_usage": model.token_usage,
            "processing_time_ms": model.processing_time_ms,
            "error_message": model.error_message or "",
            "resume_file_name": model.resume_file_name or "",
            "created_at": model.created_at.isoformat() if model.created_at else None,
        }
