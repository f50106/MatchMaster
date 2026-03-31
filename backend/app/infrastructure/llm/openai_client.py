"""OpenAI / Azure OpenAI LLM client."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import httpx
from openai import APITimeoutError, AsyncAzureOpenAI, AsyncOpenAI

from app.config import settings
from app.infrastructure.llm.base import BaseLLMClient, LLMResponse

logger = logging.getLogger(__name__)

# Models that do not support the temperature parameter (must use default=1).
_NO_TEMPERATURE_MODELS = {"o1", "o1-mini", "o3", "o3-mini", "gpt-5-mini"}


def _model_supports_temperature(model: str) -> bool:
    base = model.lower().split(":")[0]  # strip fine-tune suffixes
    return not any(base.startswith(p) for p in _NO_TEMPERATURE_MODELS)


# Separate connect / read timeouts to handle large LLM responses
# (OCR resumes can be 8K+ chars → model needs more time to generate response)
_LLM_TIMEOUT = httpx.Timeout(connect=10.0, read=240.0, write=30.0, pool=10.0)
_MAX_RETRIES = 2
_RETRY_DELAY_S = 3.0


class OpenAIClient(BaseLLMClient):
    def __init__(self) -> None:
        if settings.use_azure:
            self._client = AsyncAzureOpenAI(
                api_key=settings.azure_openai_api_key,
                azure_endpoint=settings.azure_openai_endpoint,
                api_version=settings.azure_openai_api_version,
                timeout=_LLM_TIMEOUT,
            )
            self._model = settings.azure_openai_deployment
            self._embedding_model = settings.azure_openai_embedding_deployment
        else:
            self._client = AsyncOpenAI(api_key=settings.openai_api_key, timeout=_LLM_TIMEOUT)
            self._model = settings.openai_model
            self._embedding_model = settings.openai_embedding_model

    async def chat(
        self,
        messages: list[dict[str, str]],
        response_format: type | None = None,
        temperature: float = 0.1,
    ) -> LLMResponse:
        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
        }

        # Some models (o-series, gpt-5-mini) only accept the default temperature.
        if _model_supports_temperature(self._model):
            kwargs["temperature"] = temperature

        if response_format is not None:
            # Use json_object mode instead of Structured Output (beta.parse).
            # Azure OpenAI's Structured Output requires additionalProperties: false
            # on every nested object, which is incompatible with dict[str, Any] fields.
            # json_object mode returns valid JSON without the strict schema constraint;
            # we validate it with the Pydantic model ourselves.
            kwargs["response_format"] = {"type": "json_object"}

        # Retry on timeout up to _MAX_RETRIES times
        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRIES + 1):
            try:
                response = await self._client.chat.completions.create(**kwargs)
                break
            except APITimeoutError as exc:
                last_exc = exc
                if attempt < _MAX_RETRIES:
                    wait = _RETRY_DELAY_S * (2 ** attempt)
                    logger.warning(
                        "LLM request timed out (attempt %d/%d), retrying in %.0fs",
                        attempt + 1, _MAX_RETRIES + 1, wait,
                    )
                    await asyncio.sleep(wait)
                else:
                    logger.error("LLM request timed out after %d attempts", _MAX_RETRIES + 1)
                    raise
        else:
            raise last_exc  # type: ignore[misc]

        choice = response.choices[0]
        usage = response.usage

        content = choice.message.content or ""
        parsed: dict | None = None
        if response_format is not None and content:
            try:
                raw = json.loads(content)
                instance = response_format.model_validate(raw)
                parsed = instance.model_dump()
            except Exception as exc:
                logger.warning("Failed to parse LLM response into %s: %s | raw[:300]=%r", response_format.__name__, exc, content[:300])
                parsed = None  # None signals parse failure; callers must raise, never silently default

        return LLMResponse(
            content=content,
            parsed=parsed,
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
            total_tokens=usage.total_tokens if usage else 0,
            model=response.model,
        )

    async def embed(self, texts: list[str]) -> list[list[float]]:
        response = await self._client.embeddings.create(
            model=self._embedding_model,
            input=texts,
        )
        return [item.embedding for item in response.data]
