"""Repository: Evaluation CRUD."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.models import EvaluationModel


class EvaluationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, **kwargs) -> EvaluationModel:
        obj = EvaluationModel(**kwargs)
        self._session.add(obj)
        await self._session.commit()
        await self._session.refresh(obj)
        return obj

    async def get_by_id(self, eval_id: str) -> EvaluationModel | None:
        return await self._session.get(EvaluationModel, eval_id)

    async def get_by_jd_and_resume(self, jd_id: str, resume_id: str) -> EvaluationModel | None:
        stmt = select(EvaluationModel).where(
            EvaluationModel.jd_id == jd_id,
            EvaluationModel.resume_id == resume_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def update(self, eval_id: str, **kwargs) -> EvaluationModel | None:
        obj = await self.get_by_id(eval_id)
        if not obj:
            return None
        for k, v in kwargs.items():
            setattr(obj, k, v)
        await self._session.commit()
        await self._session.refresh(obj)
        return obj

    async def list_by_jd(
        self, jd_id: str, limit: int = 100, offset: int = 0
    ) -> list[EvaluationModel]:
        stmt = (
            select(EvaluationModel)
            .where(EvaluationModel.jd_id == jd_id)
            .order_by(EvaluationModel.final_score.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def count_by_jd(self, jd_id: str) -> int:
        from sqlalchemy import func

        stmt = select(func.count()).where(EvaluationModel.jd_id == jd_id)
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def latest_created_at_by_jd(self, jd_id: str):
        """Return the max created_at datetime for all evals under a JD, or None."""
        from sqlalchemy import func
        stmt = (
            select(func.max(EvaluationModel.created_at))
            .where(EvaluationModel.jd_id == jd_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete(self, eval_id: str) -> bool:
        obj = await self.get_by_id(eval_id)
        if not obj:
            return False
        await self._session.delete(obj)
        await self._session.commit()
        return True
