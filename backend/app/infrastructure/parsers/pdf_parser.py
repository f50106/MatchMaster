"""PDF parser using PyMuPDF with section-aware extraction + OCR fallback."""

from __future__ import annotations

import asyncio
import logging
import re
from functools import partial

import pymupdf

from app.infrastructure.parsers.base import BaseParser, DocumentParseResult, ParsedSection
from app.infrastructure.parsers.section_detector import detect_heading_level

logger = logging.getLogger(__name__)

# If normal text extraction yields fewer chars than this per page on average,
# treat it as an image-based PDF and fall back to OCR.
_OCR_CHAR_THRESHOLD_PER_PAGE = 50

# OCR text cleaning: remove non-printable control chars, collapse runs of
# special chars that Tesseract hallucinates on decorative fonts.
_OCR_NOISE_RE = re.compile(
    r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]"         # control chars (keep \t \n \r)
    r"|[^\x09\x0a\x0d\x20-\x7e\u00a0-\ufffd]+"   # non-printable non-latin chars
    r"|(?:[^\w\s.,;:()\-\/]){3,}"                  # 3+ consecutive symbols in a row
, re.UNICODE)
_OCR_SPACE_RE = re.compile(r"[ \t]{3,}")           # collapse excessive whitespace
_OCR_BLANK_LINE_RE = re.compile(r"\n{3,}")         # collapse excessive blank lines


def _clean_ocr_text(text: str) -> str:
    """Remove Tesseract noise from image-based PDF OCR output."""
    text = _OCR_NOISE_RE.sub(" ", text)
    text = _OCR_SPACE_RE.sub("  ", text)
    text = _OCR_BLANK_LINE_RE.sub("\n\n", text)
    return text.strip()


class PDFParser(BaseParser):
    def supports(self, filename: str) -> bool:
        return filename.lower().endswith(".pdf")

    async def parse(self, file_path: str) -> DocumentParseResult:
        loop = asyncio.get_running_loop()
        doc = await loop.run_in_executor(None, partial(pymupdf.open, file_path))
        try:
            page_count = doc.page_count

            # ── First pass: normal text extraction ──
            all_text_parts: list[str] = []
            sections: list[ParsedSection] = []
            current_section = ParsedSection(heading="(preamble)")
            current_lines: list[str] = []

            for page in doc:
                blocks = page.get_text("dict", flags=pymupdf.TEXT_PRESERVE_WHITESPACE)["blocks"]
                for block in blocks:
                    if block["type"] != 0:  # text block
                        continue
                    for line_info in block.get("lines", []):
                        spans = line_info.get("spans", [])
                        line_text = "".join(s["text"] for s in spans).strip()
                        if not line_text:
                            continue

                        all_text_parts.append(line_text)

                        # Detect heading by font size or bold + section pattern
                        is_heading = False
                        if spans:
                            max_size = max(s.get("size", 0) for s in spans)
                            is_bold = any("bold" in s.get("font", "").lower() for s in spans)
                            pattern_level = detect_heading_level(line_text)
                            if pattern_level > 0 or (is_bold and max_size >= 12) or max_size >= 14:
                                is_heading = True

                        if is_heading:
                            # Save previous section
                            current_section.content = "\n".join(current_lines).strip()
                            if current_section.content or current_section.heading != "(preamble)":
                                sections.append(current_section)
                            current_section = ParsedSection(
                                heading=line_text, level=detect_heading_level(line_text) or 1
                            )
                            current_lines = []
                        else:
                            current_lines.append(line_text)

            # Final section
            current_section.content = "\n".join(current_lines).strip()
            if current_section.content:
                sections.append(current_section)

            raw_text = "\n".join(all_text_parts)

            # ── OCR fallback: if text is too sparse, try Tesseract ──
            total_chars = len(raw_text.strip())
            avg_chars_per_page = total_chars / max(page_count, 1)

            if avg_chars_per_page < _OCR_CHAR_THRESHOLD_PER_PAGE:
                logger.info(
                    "PDF text extraction yielded only %d chars (%d pages, %.0f/page) — "
                    "attempting OCR fallback for '%s'",
                    total_chars, page_count, avg_chars_per_page, file_path,
                )
                ocr_text = await loop.run_in_executor(None, self._ocr_extract, doc)
                if len(ocr_text.strip()) > total_chars:
                    cleaned = _clean_ocr_text(ocr_text)
                    logger.info(
                        "OCR recovered %d chars → cleaned to %d chars (was %d). Using OCR result.",
                        len(ocr_text.strip()), len(cleaned), total_chars,
                    )
                    raw_text = cleaned
                    sections = [ParsedSection(heading="(OCR)", content=cleaned)]
                else:
                    logger.warning(
                        "OCR did not improve extraction (%d chars). "
                        "PDF may be a scanned image with unreadable content.",
                        len(ocr_text.strip()),
                    )

        finally:
            doc.close()

        return DocumentParseResult(
            raw_text=raw_text,
            sections=sections,
            metadata={"page_count": page_count},
        )

    @staticmethod
    def _ocr_extract(doc: pymupdf.Document) -> str:
        """Run Tesseract OCR on each page via PyMuPDF's built-in OCR support."""
        ocr_parts: list[str] = []
        for page in doc:
            try:
                tp = page.get_textpage_ocr(flags=0, full=True)
                text = page.get_text(textpage=tp).strip()
                if text:
                    ocr_parts.append(text)
            except Exception as exc:
                logger.warning("OCR failed on page %d: %s", page.number, exc)
        return "\n\n".join(ocr_parts)
