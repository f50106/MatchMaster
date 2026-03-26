"""Keyword Overlap — TF-IDF / BM25-inspired JD-Resume keyword overlap."""

from __future__ import annotations

import math
import re
from collections import Counter

from app.domain.entities.dimension_score import DimensionScore
from app.domain.entities.job_description import ParsedJD
from app.domain.entities.resume import ParsedResume
from app.domain.scorers.base import BaseScorer

_STOPWORDS = frozenset(
    {
        "the", "a", "an", "and", "or", "in", "on", "at", "to", "for", "of", "is",
        "are", "was", "were", "be", "been", "with", "as", "by", "from", "that",
        "this", "it", "we", "you", "they", "our", "their", "will", "can",
        "的", "了", "和", "是", "在", "有", "為", "與", "之", "等", "能", "會",
    }
)


_TOKENIZE_RE = re.compile(r"[a-zA-Z\u4e00-\u9fff]+(?:[\.\-/][a-zA-Z\u4e00-\u9fff]+)*")


def _tokenize(text: str) -> list[str]:
    tokens = _TOKENIZE_RE.findall(text.lower())
    return [t for t in tokens if t not in _STOPWORDS and len(t) > 1]


class KeywordOverlap(BaseScorer):
    dimension = "keyword_overlap"

    async def score(self, jd: ParsedJD, resume: ParsedResume) -> DimensionScore:
        # Build JD keyword set from keywords + responsibilities + skills
        jd_parts: list[str] = list(jd.keywords)
        jd_parts.extend(jd.responsibilities)
        for s in jd.must_have_skills + jd.nice_to_have_skills:
            jd_parts.append(s.name)

        jd_tokens = _tokenize(" ".join(jd_parts))
        jd_counter = Counter(jd_tokens)

        # Build resume token set
        resume_parts: list[str] = list(resume.skills)
        for exp in resume.work_experiences:
            resume_parts.append(exp.description)
            resume_parts.extend(exp.skills_used)
        resume_parts.append(resume.summary)
        resume_tokens = set(_tokenize(" ".join(resume_parts)))

        if not jd_counter:
            return DimensionScore(
                dimension=self.dimension, score=50.0, weight=0.4, details="No JD keywords"
            )

        # BM25-inspired scoring
        total_jd_terms = sum(jd_counter.values())
        matched_weight = 0.0
        total_weight = 0.0
        matched_keywords: list[str] = []

        for term, freq in jd_counter.items():
            tf = freq / total_jd_terms
            idf = math.log(1 + 1 / (freq + 0.5))  # Simplified IDF
            weight = tf * idf
            total_weight += weight
            if term in resume_tokens:
                matched_weight += weight
                matched_keywords.append(term)

        overlap = matched_weight / total_weight if total_weight > 0 else 0.0
        final_score = round(min(overlap * 120, 100), 1)  # Slight boost: 83% overlap → 100

        return DimensionScore(
            dimension=self.dimension,
            score=final_score,
            weight=0.4,
            details=f"Keyword overlap: {overlap:.0%} ({len(matched_keywords)}/{len(jd_counter)} unique terms)",
            evidence=matched_keywords[:20],
        )
