"""Repository: Evaluation config CRUD."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.models import EvalConfigModel


class ConfigRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_default(self) -> EvalConfigModel | None:
        stmt = select(EvalConfigModel).where(EvalConfigModel.is_default.is_(True))
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, config_id: str) -> EvalConfigModel | None:
        return await self._session.get(EvalConfigModel, config_id)

    async def upsert_default(self, **kwargs) -> EvalConfigModel:
        existing = await self.get_default()
        if existing:
            for k, v in kwargs.items():
                setattr(existing, k, v)
            await self._session.commit()
            await self._session.refresh(existing)
            return existing
        obj = EvalConfigModel(is_default=True, name="default", **kwargs)
        self._session.add(obj)
        await self._session.commit()
        await self._session.refresh(obj)
        return obj

    async def list_all(self) -> list[EvalConfigModel]:
        stmt = select(EvalConfigModel).order_by(EvalConfigModel.created_at.desc())
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
