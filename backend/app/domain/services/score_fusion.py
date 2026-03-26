"""Score Fusion — Stage 3: combine deterministic + LLM scores.

Multi-factor confidence model + cross-validation + hard gates.
"""

from __future__ import annotations

import math

from app.domain.entities.dimension_score import DeterministicScores, LLMScores
from app.domain.entities.evaluation import Tier

# Cross-validation thresholds (surface-match detection)
_CROSS_HIGH = 80
_CROSS_LOW = 50
_CROSS_PENALTY = 3.0    # pts deducted for suspected gaming
_CROSS_BONUS = 2.0      # pts added when both stages agree strongly

# Hard gates — protect against false-positive high scores
_SKILL_HARD_GATE_THRESHOLD = 30   # must-have skill score below this triggers cap
_SKILL_HARD_GATE_CAP = 45         # max final score when hard gate triggers

# Role mismatch detection from experience evidence
_ROLE_MISMATCH_MARKER = "Role mismatch:"
_ROLE_MISMATCH_CAP = 45           # max final score for discipline mismatch
_ROLE_MISMATCH_MULTIPLIER = 0.65  # multiplicative penalty on final score


class ScoreFusion:
    def __init__(
        self,
        deterministic_weight: float = 0.35,
        llm_weight: float = 0.65,
    ) -> None:
        self._det_w = deterministic_weight
        self._llm_w = llm_weight

    # ------------------------------------------------------------------ #
    #  Public API                                                         #
    # ------------------------------------------------------------------ #

    def fuse(
        self,
        deterministic: DeterministicScores,
        llm: LLMScores,
    ) -> tuple[float, float, Tier]:
        """Return (final_score, confidence, tier)."""
        det_score = deterministic.weighted_average
        llm_score = llm.weighted_average

        final = det_score * self._det_w + llm_score * self._llm_w

        # ── Cross-validation adjustment ──
        final = self._cross_validate(final, det_score, llm_score)

        # ── Hard gate: must-have skill failure ──
        final = self._apply_skill_gate(final, deterministic)

        # ── Hard gate: role-type mismatch ──
        final = self._apply_role_mismatch_gate(final, deterministic)

        final = round(max(0, min(100, final)), 1)

        # ── Multi-factor confidence ──
        confidence = self._compute_confidence(
            deterministic, llm, det_score, llm_score, final,
        )

        tier = Tier.from_score(final)
        return final, confidence, tier

    # ------------------------------------------------------------------ #
    #  Hard gates                                                         #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _apply_skill_gate(
        final: float, det: DeterministicScores,
    ) -> float:
        """Cap final score if must-have skills are severely lacking.

        When skill_match score is below threshold, no amount of education
        or soft skills should push the candidate above the gate cap.
        """
        if det.skill_match.score < _SKILL_HARD_GATE_THRESHOLD:
            return min(final, _SKILL_HARD_GATE_CAP)
        return final

    @staticmethod
    def _apply_role_mismatch_gate(
        final: float, det: DeterministicScores,
    ) -> float:
        """Apply multiplicative penalty if the experience scorer detected
        a fundamental role-type/discipline mismatch.

        Checks the experience dimension evidence for the mismatch marker
        inserted by ExperienceCalculator + role_type.detect_role_mismatch().
        """
        for ev in det.experience.evidence:
            if _ROLE_MISMATCH_MARKER in ev:
                penalized = final * _ROLE_MISMATCH_MULTIPLIER
                return min(penalized, _ROLE_MISMATCH_CAP)
        return final

    # ------------------------------------------------------------------ #
    #  Cross-validation                                                   #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _cross_validate(
        final: float, det_score: float, llm_score: float,
    ) -> float:
        """Adjust score based on det↔LLM agreement pattern.

        High deterministic + low LLM = probable surface-optimised resume.
        Both high = genuine strong candidate.
        """
        if det_score >= _CROSS_HIGH and llm_score < _CROSS_LOW:
            # Surface match but LLM found no depth → penalise
            return final - _CROSS_PENALTY
        if det_score >= _CROSS_HIGH and llm_score >= _CROSS_HIGH:
            # Both stages agree candidate is strong → small bonus
            return final + _CROSS_BONUS
        return final

    # ------------------------------------------------------------------ #
    #  Multi-factor confidence                                            #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _compute_confidence(
        det: DeterministicScores,
        llm: LLMScores,
        det_score: float,
        llm_score: float,
        final_score: float,
    ) -> float:
        """Five-factor confidence model.

        1. Score agreement   (25%) — Gaussian tolerance of det↔LLM diff
        2. LLM evidence      (20%) — how much evidence the LLM produced
        3. Det coverage       (10%) — how many det scorers produced evidence
        4. Dimension spread   (20%) — consistency among LLM dimensions
        5. Info completeness  (25%) — how much analysable data existed
        """
        # 1. Score agreement:  Gaussian with σ=25
        #    diff=0 → 1.0, diff=15 → 0.83, diff=25 → 0.61, diff=40 → 0.28
        diff = abs(det_score - llm_score)
        agreement = math.exp(-(diff ** 2) / (2 * 25 ** 2))

        # 2. LLM evidence density  (2 items per dim = perfect)
        llm_dims = llm.all_dims
        total_evidence = sum(len(d.evidence) for d in llm_dims)
        evidence_score = min(1.0, total_evidence / 14)

        # 3. Deterministic coverage  (≥1 evidence per scorer)
        det_dims = det.all_dims
        det_with_evidence = sum(
            1 for d in det_dims if d.evidence
        )
        det_coverage = det_with_evidence / max(len(det_dims), 1)

        # 4. LLM dimension consistency (lower std → higher confidence)
        scores = [d.score for d in llm_dims]
        if scores:
            mean = sum(scores) / len(scores)
            variance = sum((s - mean) ** 2 for s in scores) / len(scores)
            std = variance ** 0.5
            consistency = max(0.0, 1.0 - std / 35)
        else:
            consistency = 0.5

        # 5. Info completeness  (based on deterministic signal richness)
        #    - skill scores produced from real skills
        #    - experience description exists
        #    - education entries exist
        signals: list[bool] = [
            det.skill_match.score > 0 or bool(det.skill_match.evidence),
            det.experience.score > 0 or bool(det.experience.evidence),
            det.education.score > 0 or bool(det.education.evidence),
            det.keyword_overlap.score > 0,
            det.red_flags.score < 100 or bool(det.red_flags.evidence),
            det.depth_analysis.score > 0 or bool(det.depth_analysis.evidence),
            det.career_progression.score > 0 or bool(det.career_progression.evidence),
        ]
        completeness = sum(signals) / len(signals)

        # Weighted combination
        confidence = (
            agreement * 0.25
            + evidence_score * 0.20
            + det_coverage * 0.10
            + consistency * 0.20
            + completeness * 0.25
        )

        return round(max(0.10, min(0.99, confidence)), 2)
