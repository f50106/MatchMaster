"""Use case: Upload and parse a Job Description."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.services.evaluation_orchestrator import EvaluationOrchestrator
from app.infrastructure.database import async_session_factory
from app.infrastructure.parsers.docx_parser import DocxParser
from app.infrastructure.parsers.pdf_parser import PDFParser
from app.infrastructure.repositories.jd_repository import JDRepository
from app.infrastructure.storage.local_storage import LocalStorage

logger = logging.getLogger(__name__)


class UploadJDUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = JDRepository(session)
        self._storage = LocalStorage()
        self._orchestrator = EvaluationOrchestrator()
        self._parsers = [PDFParser(), DocxParser()]

    async def execute(
        self, filename: str, file_content: bytes
    ) -> dict:
        """Upload JD file → parse → extract requirements → store."""
        # 1. Save file
        file_path = await self._storage.save(filename, file_content)

        # 2. Parse document
        raw_text = ""
        for parser in self._parsers:
            if parser.supports(filename):
                result = await parser.parse(file_path)
                raw_text = result.raw_text
                break
        else:
            # Fallback: treat as plain text
            raw_text = file_content.decode("utf-8", errors="replace")

        # 3. Compute cache key
        cache_key = hashlib.sha256(raw_text.encode()).hexdigest()

        # 4. Always re-run LLM extraction so users get fresh results on every upload.
        # Previous records for the same content are kept for history but not returned.
        parsed_jd, usage = await self._orchestrator.extract_jd(raw_text)

        # 5. Store in DB (creates a new record even for duplicate file content)
        jd_model = await self._repo.create(
            title=parsed_jd.title or filename,
            file_name=filename,
            raw_text=raw_text,
            parsed_requirements=parsed_jd.model_dump(),
            cache_key=cache_key,
            file_path=file_path,
        )

        return {
            "id": jd_model.id,
            "title": jd_model.title,
            "file_name": filename,
            "status": "completed",
            "is_duplicate": False,
            "parsed_requirements": parsed_jd.model_dump(),
            "token_usage": usage.model_dump(),
        }

    # ------------------------------------------------------------------ async

    async def execute_async(self, filename: str, file_content: bytes) -> dict:
        """Parse file immediately, run LLM extraction in the background.

        Returns a pending-status dict within ~100 ms so the UI can render a
        placeholder row and subscribe to the SSE progress stream.
        """
        file_path = await self._storage.save(filename, file_content)

        raw_text = ""
        for parser in self._parsers:
            if parser.supports(filename):
                result = await parser.parse(file_path)
                raw_text = result.raw_text
                break
        else:
            raw_text = file_content.decode("utf-8", errors="replace")

        cache_key = hashlib.sha256(raw_text.encode()).hexdigest()
        display_title = os.path.splitext(filename)[0]

        jd_model = await self._repo.create(
            title=display_title,
            file_name=filename,
            raw_text=raw_text,
            parsed_requirements=None,   # null = still parsing
            cache_key=cache_key,
            file_path=file_path,
        )

        asyncio.create_task(self._extract_bg(jd_model.id, raw_text))

        return {
            "id": jd_model.id,
            "title": display_title,
            "file_name": filename,
            "status": "parsing",
            "is_duplicate": False,
            "parsed_requirements": None,
            "created_at": jd_model.created_at.isoformat() if jd_model.created_at else None,
        }

    async def _extract_bg(self, jd_id: str, raw_text: str) -> None:
        """Background coroutine: run LLM extraction with its own DB session."""
        async with async_session_factory() as session:
            repo = JDRepository(session)
            try:
                parsed_jd, _usage = await self._orchestrator.extract_jd(raw_text)
                await repo.update(
                    jd_id,
                    title=parsed_jd.title or "",
                    parsed_requirements=parsed_jd.model_dump(),
                )
            except Exception:
                logger.exception("Background JD extraction failed for %s", jd_id)
                await repo.update(jd_id, parsed_requirements={"error": "extraction_failed"})
