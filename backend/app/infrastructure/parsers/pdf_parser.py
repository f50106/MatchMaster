"""PDF parser using PyMuPDF with section-aware extraction."""

from __future__ import annotations

import asyncio
from functools import partial

import pymupdf

from app.infrastructure.parsers.base import BaseParser, DocumentParseResult, ParsedSection
from app.infrastructure.parsers.section_detector import detect_heading_level


class PDFParser(BaseParser):
    def supports(self, filename: str) -> bool:
        return filename.lower().endswith(".pdf")

    async def parse(self, file_path: str) -> DocumentParseResult:
        loop = asyncio.get_running_loop()
        doc = await loop.run_in_executor(None, partial(pymupdf.open, file_path))
        try:
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

            page_count = doc.page_count
        finally:
            doc.close()

        return DocumentParseResult(
            raw_text="\n".join(all_text_parts),
            sections=sections,
            metadata={"page_count": page_count},
        )
