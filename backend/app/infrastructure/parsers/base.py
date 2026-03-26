"""Abstract base for document parsers."""

from __future__ import annotations

import abc
from dataclasses import dataclass, field


@dataclass
class ParsedSection:
    heading: str = ""
    content: str = ""
    level: int = 0  # heading level (1-6)


@dataclass
class DocumentParseResult:
    raw_text: str = ""
    sections: list[ParsedSection] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


class BaseParser(abc.ABC):
    """Base class for PDF / DOCX parsers."""

    @abc.abstractmethod
    async def parse(self, file_path: str) -> DocumentParseResult:
        ...

    @abc.abstractmethod
    def supports(self, filename: str) -> bool:
        ...
