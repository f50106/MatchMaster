"""Embedding client for skill semantic matching."""

from __future__ import annotations

import logging

import numpy as np

from app.infrastructure.llm.openai_client import OpenAIClient

logger = logging.getLogger(__name__)


class EmbeddingClient:
    def __init__(self, llm_client: OpenAIClient) -> None:
        self._llm = llm_client

    async def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return await self._llm.embed(texts)

    async def get_embedding(self, text: str) -> list[float]:
        results = await self.get_embeddings([text])
        return results[0] if results else []

    @staticmethod
    def cosine_similarity(a: list[float], b: list[float]) -> float:
        va = np.array(a, dtype=np.float32)
        vb = np.array(b, dtype=np.float32)
        dot = np.dot(va, vb)
        norm_a = np.linalg.norm(va)
        norm_b = np.linalg.norm(vb)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(dot / (norm_a * norm_b))
