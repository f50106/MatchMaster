"""Skill taxonomy with embedding-based semantic matching."""

from __future__ import annotations

import logging
from typing import Any

from app.infrastructure.cache.redis_cache import redis_cache
from app.infrastructure.embeddings.embedding_client import EmbeddingClient

logger = logging.getLogger(__name__)

_SKILL_EMB_TTL = 30 * 24 * 3600  # 30 days


class SkillTaxonomy:
    def __init__(self, embedding_client: EmbeddingClient) -> None:
        self._emb = embedding_client

    async def get_skill_embedding(self, skill_name: str) -> list[float]:
        cache_key = f"skill:emb:{skill_name.lower().strip()}"
        cached = await redis_cache.get(cache_key)
        if cached is not None:
            return cached

        embedding = await self._emb.get_embedding(skill_name)
        await redis_cache.set(cache_key, embedding, ttl_seconds=_SKILL_EMB_TTL)
        return embedding

    async def compute_skill_similarity(self, skill_a: str, skill_b: str) -> float:
        emb_a = await self.get_skill_embedding(skill_a)
        emb_b = await self.get_skill_embedding(skill_b)
        if not emb_a or not emb_b:
            return 0.0
        return EmbeddingClient.cosine_similarity(emb_a, emb_b)

    async def find_best_match(
        self, query_skill: str, candidate_skills: list[str]
    ) -> tuple[str, float]:
        """Find the best matching skill from candidates. Returns (best_skill, similarity)."""
        if not candidate_skills:
            return ("", 0.0)

        query_emb = await self.get_skill_embedding(query_skill)
        if not query_emb:
            return ("", 0.0)

        best_skill = ""
        best_sim = 0.0
        for skill in candidate_skills:
            emb = await self.get_skill_embedding(skill)
            if not emb:
                continue
            sim = EmbeddingClient.cosine_similarity(query_emb, emb)
            if sim > best_sim:
                best_sim = sim
                best_skill = skill

        return (best_skill, best_sim)

    async def batch_get_embeddings(self, skills: list[str]) -> dict[str, list[float]]:
        """Batch-fetch embeddings for multiple skills.

        Checks Redis cache for each skill and calls the embedding API only once
        for any skills that are not already cached, reducing N API calls to 1.
        """
        normalized = [s.lower().strip() for s in skills if s.strip()]
        unique = list(dict.fromkeys(normalized))  # deduplicate, preserve order

        result: dict[str, list[float]] = {}
        to_fetch: list[str] = []

        for s in unique:
            cached = await redis_cache.get(f"skill:emb:{s}")
            if cached is not None:
                result[s] = cached
            else:
                to_fetch.append(s)

        if to_fetch:
            logger.debug("Batch-embedding %d uncached skills", len(to_fetch))
            embeddings = await self._emb.get_embeddings(to_fetch)
            for skill, emb in zip(to_fetch, embeddings):
                await redis_cache.set(f"skill:emb:{skill}", emb, ttl_seconds=_SKILL_EMB_TTL)
                result[skill] = emb

        return result
