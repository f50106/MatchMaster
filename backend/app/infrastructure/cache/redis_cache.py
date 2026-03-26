"""Redis cache wrapper."""

from __future__ import annotations

import json
import logging
from typing import Any

import redis.asyncio as aioredis

from app.config import settings

logger = logging.getLogger(__name__)


class RedisCache:
    def __init__(self) -> None:
        self._redis: aioredis.Redis | None = None

    async def connect(self) -> None:
        self._redis = aioredis.from_url(settings.redis_url, decode_responses=True)

    async def disconnect(self) -> None:
        if self._redis:
            await self._redis.close()

    async def get(self, key: str) -> Any | None:
        if not self._redis:
            return None
        raw = await self._redis.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return raw

    async def set(self, key: str, value: Any, ttl_seconds: int = 3600) -> None:
        if not self._redis:
            return
        raw = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
        await self._redis.set(key, raw, ex=ttl_seconds)

    async def delete(self, key: str) -> None:
        if self._redis:
            await self._redis.delete(key)

    async def exists(self, key: str) -> bool:
        if not self._redis:
            return False
        return bool(await self._redis.exists(key))


# Singleton
redis_cache = RedisCache()
