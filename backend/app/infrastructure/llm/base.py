"""Abstract base for LLM clients."""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any


@dataclass
class LLMResponse:
    content: str = ""
    parsed: dict | None = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    model: str = ""


class BaseLLMClient(abc.ABC):
    """Abstract LLM client supporting structured output."""

    @abc.abstractmethod
    async def chat(
        self,
        messages: list[dict[str, str]],
        response_format: type | None = None,
        temperature: float = 0.1,
    ) -> LLMResponse:
        ...

    @abc.abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        ...
