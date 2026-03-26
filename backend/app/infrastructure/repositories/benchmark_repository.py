"""Repository: Calibration & Benchmark CRUD."""

from __future__ import annotations

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.models import (
    EvalBenchmarkModel,
    EvalComparisonModel,
    ScoringVersionModel,
    CalibrationFeedbackModel,
    AuthenticitySignalModel,
)


class BenchmarkRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ── Benchmarks ──

    async def create_benchmark(self, **kwargs) -> EvalBenchmarkModel:
        obj = EvalBenchmarkModel(**kwargs)
        self._session.add(obj)
        await self._session.commit()
        await self._session.refresh(obj)
        return obj

    async def get_benchmark(self, benchmark_id: str) -> EvalBenchmarkModel | None:
        return await self._session.get(EvalBenchmarkModel, benchmark_id)

    async def list_benchmarks_by_resume(
        self, jd_id: str, resume_id: str
    ) -> list[EvalBenchmarkModel]:
        stmt = (
            select(EvalBenchmarkModel)
            .where(
                EvalBenchmarkModel.jd_id == jd_id,
                EvalBenchmarkModel.resume_id == resume_id,
            )
            .order_by(EvalBenchmarkModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_benchmarks_by_source(
        self, source: str, limit: int = 50
    ) -> list[EvalBenchmarkModel]:
        stmt = (
            select(EvalBenchmarkModel)
            .where(EvalBenchmarkModel.source == source)
            .order_by(EvalBenchmarkModel.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_all_benchmarks(self, limit: int = 100) -> list[EvalBenchmarkModel]:
        stmt = (
            select(EvalBenchmarkModel)
            .order_by(EvalBenchmarkModel.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    # ── Comparisons ──

    async def create_comparison(self, **kwargs) -> EvalComparisonModel:
        obj = EvalComparisonModel(**kwargs)
        self._session.add(obj)
        await self._session.commit()
        await self._session.refresh(obj)
        return obj

    async def list_comparisons(self, limit: int = 50) -> list[EvalComparisonModel]:
        stmt = (
            select(EvalComparisonModel)
            .order_by(EvalComparisonModel.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    # ── Scoring Versions ──

    async def create_scoring_version(self, **kwargs) -> ScoringVersionModel:
        obj = ScoringVersionModel(**kwargs)
        self._session.add(obj)
        await self._session.commit()
        await self._session.refresh(obj)
        return obj

    async def get_active_version(self) -> ScoringVersionModel | None:
        stmt = (
            select(ScoringVersionModel)
            .where(ScoringVersionModel.active_to.is_(None))
            .order_by(ScoringVersionModel.active_from.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_scoring_versions(self) -> list[ScoringVersionModel]:
        stmt = select(ScoringVersionModel).order_by(
            ScoringVersionModel.active_from.desc()
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    # ── Calibration Feedback ──

    async def create_feedback(self, **kwargs) -> CalibrationFeedbackModel:
        obj = CalibrationFeedbackModel(**kwargs)
        self._session.add(obj)
        await self._session.commit()
        await self._session.refresh(obj)
        return obj

    async def list_feedback(self, limit: int = 50) -> list[CalibrationFeedbackModel]:
        stmt = (
            select(CalibrationFeedbackModel)
            .order_by(CalibrationFeedbackModel.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    # ── Authenticity Signals ──

    async def create_signal(self, **kwargs) -> AuthenticitySignalModel:
        obj = AuthenticitySignalModel(**kwargs)
        self._session.add(obj)
        await self._session.commit()
        await self._session.refresh(obj)
        return obj

    async def list_signals_by_resume(
        self, resume_id: str
    ) -> list[AuthenticitySignalModel]:
        stmt = (
            select(AuthenticitySignalModel)
            .where(AuthenticitySignalModel.resume_id == resume_id)
            .order_by(AuthenticitySignalModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    # ── Analytics ──

    async def score_drift_by_source(self) -> list[dict]:
        """Aggregate average scores per source for drift analysis."""
        stmt = (
            select(
                EvalBenchmarkModel.source,
                func.count().label("count"),
                func.avg(EvalBenchmarkModel.overall_score).label("avg_score"),
                func.min(EvalBenchmarkModel.overall_score).label("min_score"),
                func.max(EvalBenchmarkModel.overall_score).label("max_score"),
            )
            .group_by(EvalBenchmarkModel.source)
        )
        result = await self._session.execute(stmt)
        return [
            {
                "source": row.source,
                "count": row.count,
                "avg_score": round(float(row.avg_score or 0), 1),
                "min_score": round(float(row.min_score or 0), 1),
                "max_score": round(float(row.max_score or 0), 1),
            }
            for row in result.all()
        ]
