"""Local filesystem storage."""

from __future__ import annotations

import asyncio
import os
import uuid
from pathlib import Path

from app.config import settings
from app.infrastructure.storage.base import BaseStorage

_ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt"}


class LocalStorage(BaseStorage):
    def __init__(self) -> None:
        self._base = Path(settings.upload_dir)
        self._base.mkdir(parents=True, exist_ok=True)

    async def save(self, filename: str, content: bytes) -> str:
        # Validate filename to prevent path traversal
        safe_name = os.path.basename(filename)
        ext = Path(safe_name).suffix.lower()
        if ext not in _ALLOWED_EXTENSIONS:
            raise ValueError(f"Unsupported file type: {ext}")
        unique_name = f"{uuid.uuid4().hex}{ext}"
        dest = self._base / unique_name
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, dest.write_bytes, content)
        return str(dest)

    def _check_path(self, path: str) -> Path:
        """Resolve and validate that path is inside base directory."""
        resolved = Path(path).resolve()
        base_resolved = self._base.resolve()
        if not resolved.is_relative_to(base_resolved):
            raise PermissionError("Access denied")
        return resolved

    async def read(self, path: str) -> bytes:
        resolved = self._check_path(path)
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, resolved.read_bytes)

    async def delete(self, path: str) -> None:
        resolved = self._check_path(path)
        if resolved.exists():
            resolved.unlink()
