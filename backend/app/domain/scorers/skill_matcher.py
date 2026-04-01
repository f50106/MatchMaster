"""Skill Matcher — embedding cosine similarity for must-have / nice-to-have skills.

Uses graduated scoring instead of binary threshold:
  sim >= 0.80  → full credit (strong match)
  0.60 - 0.80  → partial credit (related / equivalent skill)
  < 0.60       → no credit (unrelated)
"""

from __future__ import annotations

from app.domain.entities.dimension_score import DimensionScore
from app.domain.entities.job_description import ParsedJD
from app.domain.entities.resume import ParsedResume
from app.domain.scorers.base import BaseScorer
from app.infrastructure.embeddings.embedding_client import EmbeddingClient
from app.infrastructure.embeddings.skill_taxonomy import SkillTaxonomy

_MUST_HAVE_WEIGHT = 0.7
_NICE_TO_HAVE_WEIGHT = 0.3

# Graduated thresholds (no binary cliff)
_SIM_FULL = 0.80    # >= this → full credit
_SIM_PARTIAL = 0.60  # >= this → partial credit (linear interpolation)
_SIM_FLOOR = 0.45    # >= this → minimal credit


def _graduated_score(sim: float) -> float:
    """Convert raw cosine similarity to a graduated skill score.

    Avoids the binary cliff problem where 0.74 = 0 and 0.76 = full credit.
    """
    if sim >= _SIM_FULL:
        return 1.0
    if sim >= _SIM_PARTIAL:
        # Linear ramp: 0.60 → 0.50,  0.70 → 0.75,  0.80 → 1.0
        return 0.50 + 0.50 * (sim - _SIM_PARTIAL) / (_SIM_FULL - _SIM_PARTIAL)
    if sim >= _SIM_FLOOR:
        # Low credit for loosely related skills: 0.45 → 0.10, 0.60 → 0.50
        return 0.10 + 0.40 * (sim - _SIM_FLOOR) / (_SIM_PARTIAL - _SIM_FLOOR)
    return 0.0


class SkillMatcher(BaseScorer):
    dimension = "skill_match"

    def __init__(self, taxonomy: SkillTaxonomy) -> None:
        self._taxonomy = taxonomy

    async def score(self, jd: ParsedJD, resume: ParsedResume) -> DimensionScore:
        candidate_skills = [s.lower().strip() for s in resume.skills]

        # Also include skills_used from work experiences for richer matching
        exp_skills: list[str] = []
        for exp in resume.work_experiences:
            for s in exp.skills_used:
                normalized = s.lower().strip()
                if normalized and normalized not in candidate_skills:
                    exp_skills.append(normalized)
        all_candidate_skills = candidate_skills + exp_skills

        # Collect all unique skill names and batch-embed them in ONE API call.
        jd_skill_names = [r.name for r in jd.must_have_skills] + [r.name for r in jd.nice_to_have_skills]
        all_unique = list(dict.fromkeys(jd_skill_names + all_candidate_skills))
        emb_map = await self._taxonomy.batch_get_embeddings(all_unique)

        def find_best_local(query: str) -> tuple[str, float]:
            q_emb = emb_map.get(query.lower().strip(), [])
            if not q_emb:
                return ("", 0.0)
            best_skill, best_sim = "", 0.0
            for cand in all_candidate_skills:
                c_emb = emb_map.get(cand, [])
                if not c_emb:
                    continue
                sim = EmbeddingClient.cosine_similarity(q_emb, c_emb)
                if sim > best_sim:
                    best_sim = sim
                    best_skill = cand
            return best_skill, best_sim

        evidence: list[str] = []

        # Must-have skills — graduated scoring
        must_scores: list[float] = []
        for req in jd.must_have_skills:
            best_skill, sim = find_best_local(req.name)
            grad = _graduated_score(sim)
            must_scores.append(grad)
            if sim >= 0.90:
                evidence.append(f"✓ {req.name} → {best_skill} ({sim:.0%})")
            elif sim >= 0.60:
                evidence.append(f"△ {req.name} ~ {best_skill} ({sim:.0%})")
            else:
                evidence.append(f"✗ {req.name} — not found (best: {best_skill} {sim:.0%})")

        # Nice-to-have skills — graduated scoring
        nice_scores: list[float] = []
        for req in jd.nice_to_have_skills:
            best_skill, sim = find_best_local(req.name)
            grad = _graduated_score(sim)
            nice_scores.append(grad)
            if sim >= _SIM_PARTIAL:
                evidence.append(f"☆ {req.name} → {best_skill} ({sim:.0%})")

        # Weight redistribution: when one category is absent, all weight
        # goes to the other.  When BOTH are absent, score is neutral (0.5).
        if must_scores and nice_scores:
            must_avg = sum(must_scores) / len(must_scores)
            nice_avg = sum(nice_scores) / len(nice_scores)
            raw_score = must_avg * _MUST_HAVE_WEIGHT + nice_avg * _NICE_TO_HAVE_WEIGHT
        elif must_scores:
            must_avg = sum(must_scores) / len(must_scores)
            nice_avg = 0.0
            raw_score = must_avg  # 100% on must-have
        elif nice_scores:
            must_avg = 0.0
            nice_avg = sum(nice_scores) / len(nice_scores)
            raw_score = nice_avg  # 100% on nice-to-have
        else:
            must_avg = 0.0
            nice_avg = 0.0
            raw_score = 0.5  # No skill requirements — true neutral
        final_score = round(raw_score * 100, 1)

        return DimensionScore(
            dimension=self.dimension,
            score=final_score,
            weight=1.5,
            details=f"Must-have: {must_avg:.0%}, Nice-to-have: {nice_avg:.0%}",
            evidence=evidence,
        )
