"""API v1: Configuration endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import get_db
from app.infrastructure.repositories.config_repository import ConfigRepository

router = APIRouter(prefix="/configs", tags=["Configuration"])


class ConfigUpdateRequest(BaseModel):
    dimension_weights: dict[str, float] | None = None
    deterministic_weight: float | None = None
    llm_weight: float | None = None
    model_name: str | None = None


@router.get("")
async def get_config(db: AsyncSession = Depends(get_db)):
    """Get current evaluation configuration."""
    repo = ConfigRepository(db)
    config = await repo.get_default()
    if not config:
        return {
            "dimension_weights": {},
            "deterministic_weight": 0.4,
            "llm_weight": 0.6,
            "model_name": "gpt-4o",
        }
    return {
        "id": config.id,
        "name": config.name,
        "dimension_weights": config.dimension_weights,
        "deterministic_weight": config.deterministic_weight,
        "llm_weight": config.llm_weight,
        "model_name": config.model_name,
    }


@router.put("")
async def update_config(
    body: ConfigUpdateRequest, db: AsyncSession = Depends(get_db)
):
    """Update evaluation configuration."""
    repo = ConfigRepository(db)
    kwargs = {k: v for k, v in body.model_dump().items() if v is not None}
    config = await repo.upsert_default(**kwargs)
    return {
        "id": config.id,
        "name": config.name,
        "dimension_weights": config.dimension_weights,
        "deterministic_weight": config.deterministic_weight,
        "llm_weight": config.llm_weight,
        "model_name": config.model_name,
    }
