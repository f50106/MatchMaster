"""Abstract base for file storage."""

from __future__ import annotations

import abc


class BaseStorage(abc.ABC):
    @abc.abstractmethod
    async def save(self, filename: str, content: bytes) -> str:
        """Save file, return stored path."""
        ...

    @abc.abstractmethod
    async def read(self, path: str) -> bytes:
        ...

    @abc.abstractmethod
    async def delete(self, path: str) -> None:
        ...
