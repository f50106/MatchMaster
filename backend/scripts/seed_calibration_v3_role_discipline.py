"""Seed calibration v3 — Gemini cross-comparison for Developer JD role-discipline mismatch.

Context:
  - JD: Software Developer position
  - Candidates: QA/SDET professionals applying to a Developer role
  - Problem discovered: QA candidates were scoring 60+ for a Dev position
  - Gemini analysis identified 5 critical scoring flaws
  - v3.0.0 fixes: role_type.py, domain-aware experience, hard gates, prompt debiasing
  - Date: 2026-03-24
"""

import asyncio
import sys

sys.path.insert(0, "/app")

from app.infrastructure.database import async_session_factory
from app.application.calibration_service import CalibrationService


async def main():
    async with async_session_factory() as session:
        svc = CalibrationService(session)

        # ──────────────────────────────────────────
        # 1. Scoring Version v3.0.0-role-discipline
        # ──────────────────────────────────────────
        v3 = await svc.snapshot_scoring_version(
            "v3.0.0-role-discipline",
            deterministic_weights={
                "skill_match": 1.5,
                "experience": 1.5,
                "education": {"dynamic": "0.4-0.8", "seniority_decay": True},
                "keyword_overlap": 0.5,
                "red_flags": 0.8,
                "depth_analysis": 0.8,
                "career_progression": 0.6,
            },
            llm_weights={
                "technical_skills": 1.5,
                "work_experience": 2.0,
                "education": 0.6,
                "career_trajectory": 1.5,
                "red_flags": 0.8,
                "soft_skills": 1.0,
                "language_fit": 0.4,
            },
            fusion_config={
                "deterministic_weight": 0.35,
                "llm_weight": 0.65,
                "cross_high": 80,
                "cross_low": 50,
                "cross_penalty": 3.0,
                "cross_bonus": 2.0,
                "skill_hard_gate_threshold": 30,
                "skill_hard_gate_cap": 45,
                "role_mismatch_cap": 45,
                "role_mismatch_multiplier": 0.65,
            },
            changes_description=(
                "v3.0.0-role-discipline: Critical scoring calibration overhaul. "
                "Gemini cross-comparison exposed QA candidates scoring 60+ for Developer positions. "
                "5 root causes fixed:\n"
                "1. NEW role_type.py — discipline taxonomy (qa/devops/data/design/pm/development), "
                "   classify_title() + detect_role_mismatch() with 70% threshold\n"
                "2. experience_calc.py — 3-factor scoring (years 45% + industry 25% + role-fit 30%), "
                "   mismatch years discounted to 15% value (11y QA → 1.65y effective for Dev)\n"
                "3. score_fusion.py — must-have skill hard gate (skill_match < 30 → cap at 45), "
                "   role mismatch gate (× 0.65 + cap at 45)\n"
                "4. consolidated_eval.jinja2 — LLM prompt debiased: "
                "   philosophy from 'not looking for reasons to reject' → 'evaluate objective fit honestly', "
                "   NEW principle 6 (role-type mismatch = strongest disqualifier with explicit score ceilings), "
                "   skill equivalence now discipline-gated, context-aware skill evaluation, "
                "   stricter score calibration (30-44 = fundamentally mismatched discipline), "
                "   each dimension instruction updated with role-mismatch awareness\n"
                "5. consolidated_eval.jinja2 — all output forced to English only (was 'same language as JD')\n"
                "6. Frontend — DimCard ordering fixed to follow DET_DIMS/LLM_DIMS arrays"
            ),
        )
        print(f"Created v3.0.0-role-discipline: {v3.id}")

        # ──────────────────────────────────────────
        # 2. Gemini Analysis — Developer JD vs QA Candidates
        #    (Gemini identified 5 flaws in v2 scoring)
        # ──────────────────────────────────────────

        # Context: JD was a Software Developer/Engineer position
        # QA candidates were evaluated and scored 60+ because:
        # - Role mismatch not detected or penalized
        # - Experience years counted at face value regardless of discipline
        # - LLM gave "participation trophy" scores
        # - Keyword overlap inflated (shared tools like Azure, SQL, Git)
        # - Career trajectory in QA was scored positively for Dev role

        gemini_analysis = await svc.import_external_eval(
            source="gemini",
            source_version="gemini-2.5-pro",
            candidate_name="[Aggregate QA Candidates]",
            jd_title="Software Developer (analysis target)",
            overall_score=None,  # Meta-analysis, not individual eval
            tier="",
            dimension_scores={
                "flaw_1_role_mismatch": (
                    "The scoring pipeline has no concept of role-type or discipline mismatch. "
                    "A QA engineer with 11 years experience is evaluated the same as a developer with 11 years. "
                    "The experience scorer treats all years equally — 11y QA = 11y Dev. "
                    "This is the root cause: the system cannot distinguish between disciplines."
                ),
                "flaw_2_domain_agnostic_experience": (
                    "ExperienceCalculator only checks years_ratio (0.6) and industry_ratio (0.4). "
                    "There is zero awareness of role category — QA, Dev, DevOps are all treated identically. "
                    "A QA lead's 11 years produces the same experience score as a senior developer's 11 years "
                    "when both target industries match."
                ),
                "flaw_3_llm_participation_trophy": (
                    "The LLM prompt's evaluation philosophy says 'not looking for reasons to reject' and "
                    "'acknowledge potential'. This creates systematic upward bias. "
                    "A QA candidate gets 60+ because the LLM finds SOMETHING positive to say about education, "
                    "soft skills, and years of experience — even though the core discipline is wrong. "
                    "The LLM treats 'used Azure' in test deployment context = 'used Azure' in PaaS development, "
                    "inflating technical_skills scores."
                ),
                "flaw_4_keyword_semantic_ambiguity": (
                    "Shared keywords between QA and Dev (Azure, SQL, Git, Python, CI/CD, Docker) produce "
                    "misleading skill_match and keyword_overlap scores. "
                    "A QA engineer who used SQL for test data setup gets cosine similarity credit "
                    "against a JD requiring SQL for database design and optimization. "
                    "The embedding model cannot distinguish usage context."
                ),
                "flaw_5_career_trajectory_misread": (
                    "Career trajectory scorer treats progressive seniority as positive regardless of discipline. "
                    "Junior QA → Senior QA → QA Lead → SDET is scored as a STRONG trajectory, "
                    "but for a Developer JD this trajectory is actually evidence of MISMATCH — "
                    "the candidate has been deepening in the WRONG discipline for their entire career."
                ),
            },
            analysis_text=(
                "Gemini Cross-Comparison Analysis: Developer JD Scoring Accuracy (2026-03-24)\n\n"
                "## Problem Statement\n"
                "QA/SDET candidates were consistently scoring 60+ when evaluated against Software Developer "
                "positions. This makes the system unable to effectively distinguish good from bad candidates "
                "for a given role — the core purpose of the tool.\n\n"
                "## 5 Root Causes Identified\n\n"
                "### 1. No Role-Type Mismatch Detection\n"
                "The scoring pipeline has no concept of 'discipline'. All job titles are treated equally. "
                "A QA Engineer, Software Developer, DevOps Engineer, and Data Analyst all flow through "
                "the same scoring path with zero role-type awareness. When a QA engineer applies for a "
                "Dev position, the system doesn't recognize this as a fundamentally different discipline.\n\n"
                "### 2. Domain-Agnostic Experience Scoring\n"
                "ExperienceCalculator uses years × 0.6 + industry × 0.4. If both candidates have 10 years "
                "in the same industry, they score identically — even if one is QA and one is Dev. "
                "The years are counted at face value with no discipline discount. "
                "11 years of QA ≠ 11 years of development for a developer position.\n\n"
                "### 3. LLM 'Participation Trophy' Bias\n"
                "The prompt says 'not looking for reasons to reject' and 'acknowledge potential'. "
                "This causes the LLM to find positives even in mismatched candidates: "
                "'The candidate has strong QA experience which provides testing perspective' → 65/100. "
                "It treats skill adjacency as skill match: 'used Python for test scripts' → partial credit "
                "for a JD requiring Python application development.\n\n"
                "### 4. Keyword Semantic Ambiguity\n"
                "Technologies shared across disciplines (Azure, SQL, Git, Python, Docker, CI/CD) produce "
                "misleading cosine similarity scores. The embedding model matches 'Azure' to 'Azure' "
                "regardless of whether it was used for test deployment or for PaaS architecture design. "
                "This inflates both skill_match and keyword_overlap for cross-discipline candidates.\n\n"
                "### 5. Career Trajectory Misinterpretation\n"
                "The career progression scorer rewards seniority progression unconditionally. "
                "A trajectory of Junior QA → Senior QA → QA Lead → SDET Manager is rated as 'strong growth', "
                "but for a Developer position, this is actually NEGATIVE evidence — the candidate's entire "
                "career has been deepening in a different discipline.\n\n"
                "## Expected Impact of Fixes\n"
                "- QA candidate for Dev JD: score should drop from ~60+ to ~25-40\n"
                "- Correct Developer candidate: score should remain 70-90+\n"
                "- Cross-discipline with genuine transition evidence: 45-55\n"
                "- Net effect: system can now DIFFERENTIATE good from bad candidates for a given role"
            ),
            strengths=[],
            weaknesses=[
                "No role-type/discipline awareness in scoring pipeline",
                "Experience years counted at face value regardless of role match",
                "LLM prompt systematically inflates scores for mismatched candidates",
                "Shared keywords (Azure/SQL/Git) create false positive similarity",
                "Career trajectory rewards wrong-discipline seniority growth",
            ],
        )
        print(f"Gemini meta-analysis: {gemini_analysis.id}")

        # ──────────────────────────────────────────
        # 3. Calibration Feedback — v2 → v3 transition
        # ──────────────────────────────────────────
        await svc.submit_feedback(
            accuracy_rating=3,
            feedback_text=(
                "v2_graduated / v2.1.0-seniority-decay scoring insufficient for cross-discipline detection. "
                "QA candidates scored 60+ on Developer JD — system failed core differentiation purpose. "
                "5 root causes identified via Gemini cross-comparison:\n"
                "1. No role-type/discipline mismatch detection\n"
                "2. Experience years domain-agnostic (11y QA = 11y Dev)\n"
                "3. LLM 'participation trophy' bias ('not looking for reasons to reject')\n"
                "4. Keyword semantic ambiguity (Azure for testing ≈ Azure for development)\n"
                "5. Career trajectory rewards wrong-discipline seniority\n\n"
                "Human judgment: A QA engineer with 11 years should score 25-40 for a Developer role, "
                "not 60+. The system was fundamentally unable to distinguish good from bad candidates "
                "when the mismatch was at the discipline level rather than the skill level."
            ),
            action_taken=(
                "Created v3.0.0-role-discipline with 6 changes:\n"
                "1. NEW role_type.py — 6-discipline taxonomy with title classification + mismatch detection\n"
                "2. experience_calc.py — 3-factor scoring (years 45% + industry 25% + role-fit 30%), "
                "   mismatch years discounted to 15% of face value\n"
                "3. score_fusion.py — must-have skill hard gate (score<30 → cap 45), "
                "   role mismatch multiplicative gate (×0.65 + cap 45)\n"
                "4. consolidated_eval.jinja2 — prompt debiased: "
                "   objective fit philosophy, discipline-gated skill equivalence, "
                "   context-aware skill evaluation, explicit role-mismatch scoring ceilings, "
                "   stricter calibration scale\n"
                "5. consolidated_eval.jinja2 — all LLM output forced to English only\n"
                "6. EvaluationPage.tsx — DimCard ordering fixed to follow DET_DIMS/LLM_DIMS arrays"
            ),
            scoring_version_id=v3.id,
        )
        print("Calibration feedback v2→v3 recorded.")

        # ──────────────────────────────────────────
        # 4. Cross-Comparison: v2 behavior vs v3 expected behavior
        # ──────────────────────────────────────────
        v2_behavior = await svc.import_external_eval(
            source="matchmaster",
            source_version="v2_graduated",
            candidate_name="[Typical QA Candidate for Dev JD]",
            jd_title="Software Developer",
            overall_score=62.0,
            tier="B",
            dimension_scores={
                "deterministic": {
                    "skill_match": 18.8,
                    "experience": 72.0,
                    "education": 65.0,
                    "keyword_overlap": 45.0,
                    "red_flags": 85.0,
                    "depth_analysis": 55.0,
                    "career_progression": 70.0,
                },
                "llm": {
                    "technical_skills": 55.0,
                    "work_experience": 65.0,
                    "education": 70.0,
                    "career_trajectory": 60.0,
                    "red_flags": 90.0,
                    "soft_skills": 75.0,
                    "language_fit": 80.0,
                },
            },
            analysis_text=(
                "v2 behavior: QA candidate with 11y experience, strong QA tooling (Selenium, Playwright, "
                "NUnit, JIRA), applying for Software Developer position. "
                "Skill match low (18.8%) but high experience/education/soft skills inflate final score to 62. "
                "LLM gives 55-65 on technical/experience because of 'participation trophy' bias. "
                "No hard gates triggered because skill_gate was removed in v2."
            ),
        )
        print(f"v2 behavior benchmark: {v2_behavior.id}")

        v3_expected = await svc.import_external_eval(
            source="matchmaster",
            source_version="v3.0.0-role-discipline",
            candidate_name="[Typical QA Candidate for Dev JD]",
            jd_title="Software Developer",
            overall_score=28.0,
            tier="D",
            dimension_scores={
                "deterministic": {
                    "skill_match": 18.8,
                    "experience": 25.0,
                    "education": 65.0,
                    "keyword_overlap": 45.0,
                    "red_flags": 85.0,
                    "depth_analysis": 55.0,
                    "career_progression": 70.0,
                },
                "llm": {
                    "technical_skills": 30.0,
                    "work_experience": 35.0,
                    "education": 70.0,
                    "career_trajectory": 35.0,
                    "red_flags": 90.0,
                    "soft_skills": 75.0,
                    "language_fit": 80.0,
                },
            },
            analysis_text=(
                "v3 expected behavior: Same QA candidate now gets role-type mismatch detection. "
                "Experience years discounted from 11y → 1.65y effective (15% of face value). "
                "Experience score drops from 72 → ~25. "
                "LLM debiased prompt scores technical_skills ~30, work_experience ~35, career_trajectory ~35. "
                "Skill hard gate triggered (18.8 < 30) → cap at 45. "
                "Role mismatch gate triggered → ×0.65 + cap at 45. "
                "Final score ~28-35 (D tier) — correctly identifies as poor fit for Developer role."
            ),
        )
        print(f"v3 expected benchmark: {v3_expected.id}")

        cmp_v2_v3 = await svc.create_cross_comparison(
            benchmark_a_id=v2_behavior.id,
            benchmark_b_id=v3_expected.id,
            comparison_text=(
                "v2 vs v3: QA Candidate for Developer JD\n\n"
                "v2 score: ~62 (B tier) — INCORRECT, should be rejected\n"
                "v3 expected: ~28 (D tier) — CORRECT, clearly identifies discipline mismatch\n\n"
                "Key Changes:\n"
                "1. Experience: 72 → 25 (role-fit factor penalizes QA years for Dev role)\n"
                "2. LLM technical_skills: 55 → 30 (debiased prompt recognizes discipline mismatch)\n"
                "3. LLM work_experience: 65 → 35 (QA years ≠ Dev years per new prompt)\n"
                "4. LLM career_trajectory: 60 → 35 (QA seniority growth = wrong direction)\n"
                "5. Skill hard gate: caps at 45 (skill_match 18.8 < 30)\n"
                "6. Role mismatch gate: ×0.65 + cap at 45\n\n"
                "Net effect: 34-point score reduction for fundamentally mismatched candidate. "
                "System can now differentiate QA from Dev candidates."
            ),
            key_differences=[
                "Role-type mismatch detection (NEW in v3)",
                "Experience years discipline-discounted (15% for wrong discipline)",
                "LLM prompt debiased (objective fit vs participation trophy)",
                "Must-have skill hard gate re-introduced (cap at 45)",
                "Role mismatch multiplicative gate (×0.65 + cap 45)",
                "Score drop: 62 → 28 for discipline-mismatched candidate",
            ],
            preferred_source="v3.0.0-role-discipline",
            accuracy_notes=(
                "v3 correctly identifies QA→Dev mismatch as fundamentally unqualified (D tier). "
                "v2 falsely ranked them as B tier — indistinguishable from a mediocre Dev candidate. "
                "Human judgment agrees with v3: a QA engineer should score 25-40 for Dev role."
            ),
            compared_by="gemini-cross-analysis",
        )
        print(f"v2 vs v3 comparison: {cmp_v2_v3.id}")

        print("\n✅ v3 calibration seed complete.")


if __name__ == "__main__":
    asyncio.run(main())
