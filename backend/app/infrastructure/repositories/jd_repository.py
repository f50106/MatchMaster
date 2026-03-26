"""Repository: Job Description CRUD."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.models import JobDescriptionModel


class JDRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, **kwargs) -> JobDescriptionModel:
        obj = JobDescriptionModel(**kwargs)
        self._session.add(obj)
        await self._session.commit()
        await self._session.refresh(obj)
        return obj

    async def get_by_id(self, jd_id: str) -> JobDescriptionModel | None:
        return await self._session.get(JobDescriptionModel, jd_id)

    async def get_by_cache_key(self, cache_key: str) -> JobDescriptionModel | None:
        stmt = select(JobDescriptionModel).where(JobDescriptionModel.cache_key == cache_key)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def update(self, jd_id: str, **kwargs) -> JobDescriptionModel | None:
        obj = await self.get_by_id(jd_id)
        if not obj:
            return None
        for k, v in kwargs.items():
            setattr(obj, k, v)
        await self._session.commit()
        await self._session.refresh(obj)
        return obj

    async def list_all(self, limit: int = 50, offset: int = 0) -> list[JobDescriptionModel]:
        stmt = (
            select(JobDescriptionModel)
            .order_by(JobDescriptionModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def delete(self, jd_id: str) -> bool:
        obj = await self.get_by_id(jd_id)
        if not obj:
            return False
        await self._session.delete(obj)
        await self._session.commit()
        return True
