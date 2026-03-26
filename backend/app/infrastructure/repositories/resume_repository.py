"""Repository: Resume CRUD."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.models import ResumeModel


class ResumeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, **kwargs) -> ResumeModel:
        obj = ResumeModel(**kwargs)
        self._session.add(obj)
        await self._session.commit()
        await self._session.refresh(obj)
        return obj

    async def get_by_id(self, resume_id: str) -> ResumeModel | None:
        return await self._session.get(ResumeModel, resume_id)

    async def get_by_file_hash(self, file_hash: str) -> ResumeModel | None:
        stmt = select(ResumeModel).where(ResumeModel.file_hash == file_hash)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def update(self, resume_id: str, **kwargs) -> ResumeModel | None:
        obj = await self.get_by_id(resume_id)
        if not obj:
            return None
        for k, v in kwargs.items():
            setattr(obj, k, v)
        await self._session.commit()
        await self._session.refresh(obj)
        return obj
