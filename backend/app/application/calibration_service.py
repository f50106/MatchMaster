"""Calibration service — snapshot config, import evaluations, track drift."""

from __future__ import annotations

import hashlib
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.repositories.benchmark_repository import BenchmarkRepository

logger = logging.getLogger(__name__)


class CalibrationService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = BenchmarkRepository(session)

    async def snapshot_scoring_version(
        self,
        version_name: str,
        *,
        deterministic_weights: dict | None = None,
        llm_weights: dict | None = None,
        fusion_config: dict | None = None,
        prompt_text: str = "",
        changes_description: str = "",
    ):
        """Save a snapshot of the current scoring pipeline configuration."""
        prompt_hash = (
            hashlib.sha256(prompt_text.encode()).hexdigest()[:16]
            if prompt_text
            else ""
        )
        return await self._repo.create_scoring_version(
            version_name=version_name,
            deterministic_weights=deterministic_weights,
            llm_weights=llm_weights,
            fusion_config=fusion_config,
            prompt_hash=prompt_hash,
            changes_description=changes_description,
        )

    async def import_matchmaster_eval(
        self,
        *,
        jd_id: str,
        resume_id: str,
        candidate_name: str,
        jd_title: str,
        jd_file_name: str = "",
        resume_file_name: str = "",
        overall_score: float,
        tier: str,
        deterministic_scores: dict | None = None,
        llm_scores: dict | None = None,
        meta_summary: str = "",
        interview_questions: list | None = None,
        scoring_version_id: str | None = None,
        source_version: str = "v2_graduated",
    ):
        """Import a MatchMaster evaluation into benchmarks for comparison."""
        return await self._repo.create_benchmark(
            jd_id=jd_id,
            resume_id=resume_id,
            source="matchmaster",
            source_version=source_version,
            scoring_version_id=scoring_version_id,
            overall_score=overall_score,
            tier=tier,
            dimension_scores={
                "deterministic": deterministic_scores,
                "llm": llm_scores,
            },
            analysis_text=meta_summary,
            interview_questions=interview_questions,
            candidate_name=candidate_name,
            jd_title=jd_title,
            jd_file_name=jd_file_name,
            resume_file_name=resume_file_name,
        )

    async def import_external_eval(
        self,
        *,
        source: str,
        source_version: str,
        candidate_name: str = "",
        jd_title: str = "",
        jd_id: str | None = None,
        resume_id: str | None = None,
        overall_score: float | None = None,
        tier: str = "",
        dimension_scores: dict | None = None,
        analysis_text: str = "",
        strengths: list[str] | None = None,
        weaknesses: list[str] | None = None,
        interview_questions: list[str] | None = None,
        raw_data: dict | None = None,
    ):
        """Import an evaluation from an external model (Gemini, Claude, etc.)."""
        return await self._repo.create_benchmark(
            jd_id=jd_id,
            resume_id=resume_id,
            source=source,
            source_version=source_version,
            overall_score=overall_score,
            tier=tier,
            dimension_scores=dimension_scores,
            analysis_text=analysis_text,
            strengths=strengths,
            weaknesses=weaknesses,
            interview_questions=interview_questions,
            candidate_name=candidate_name,
            jd_title=jd_title,
            raw_data=raw_data,
        )

    async def create_cross_comparison(
        self,
        *,
        benchmark_a_id: str,
        benchmark_b_id: str,
        comparison_text: str,
        key_differences: list[str] | None = None,
        preferred_source: str = "",
        accuracy_notes: str = "",
        compared_by: str = "user",
    ):
        """Record a side-by-side comparison between two evaluations."""
        return await self._repo.create_comparison(
            benchmark_a_id=benchmark_a_id,
            benchmark_b_id=benchmark_b_id,
            comparison_text=comparison_text,
            key_differences=key_differences,
            preferred_source=preferred_source,
            accuracy_notes=accuracy_notes,
            compared_by=compared_by,
        )

    async def submit_feedback(
        self,
        *,
        benchmark_id: str | None = None,
        human_score: float | None = None,
        human_tier: str = "",
        accuracy_rating: int | None = None,
        feedback_text: str = "",
        dimension_adjustments: dict | None = None,
        action_taken: str = "",
        scoring_version_id: str | None = None,
    ):
        """Submit calibration feedback on an evaluation's accuracy."""
        return await self._repo.create_feedback(
            benchmark_id=benchmark_id,
            human_score=human_score,
            human_tier=human_tier,
            accuracy_rating=accuracy_rating,
            feedback_text=feedback_text,
            dimension_adjustments=dimension_adjustments,
            action_taken=action_taken,
            scoring_version_id=scoring_version_id,
        )

    async def get_score_drift(self) -> list[dict]:
        """Get avg score by source for drift analysis."""
        return await self._repo.score_drift_by_source()
