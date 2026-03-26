"""Seed calibration data from session — v1 evals, Gemini analyses, comparisons."""

import asyncio
import sys

# Ensure the app module is importable
sys.path.insert(0, "/app")

from app.infrastructure.database import async_session_factory
from app.application.calibration_service import CalibrationService

JD_ID = "aa5559e5c6ab47d1b73dde49e314b18d"
JD_TITLE = "Senior Software Test Engineer"
JD_FILE = "WITS India Senior Software Test Engineer JD - Bangalore (1).pdf"


async def main():
    async with async_session_factory() as session:
        svc = CalibrationService(session)

        # ──────────────────────────────────────────
        # 1. Scoring Versions
        # ──────────────────────────────────────────
        v1 = await svc.snapshot_scoring_version(
            "v1_binary",
            deterministic_weights={
                "skill_match": 2.0,
                "experience": 1.5,
                "education": 1.0,
                "keyword_overlap": 1.0,
                "red_flags": 1.0,
                "depth_analysis": 1.5,
            },
            llm_weights={
                "technical_skills": 1.5,
                "work_experience": 1.5,
                "education": 0.8,
                "career_trajectory": 1.2,
                "red_flags": 1.0,
                "soft_skills": 0.8,
                "language_fit": 0.5,
            },
            fusion_config={
                "deterministic_weight": 0.40,
                "llm_weight": 0.60,
                "skill_gate_hard": 30,
                "skill_gate_soft": 50,
                "cross_high": 75,
                "cross_low": 55,
            },
            changes_description="Initial binary threshold scoring. cosine>0.75=match, <0.75=0. Hard skill gate caps.",
        )
        print(f"Created v1_binary: {v1.id}")

        v2 = await svc.snapshot_scoring_version(
            "v2_graduated",
            deterministic_weights={
                "skill_match": 1.5,
                "experience": 1.5,
                "education": 1.0,
                "keyword_overlap": 1.0,
                "red_flags": 1.0,
                "depth_analysis": 0.8,
            },
            llm_weights={
                "technical_skills": 1.5,
                "work_experience": 1.5,
                "education": 0.6,
                "career_trajectory": 1.5,
                "red_flags": 0.8,
                "soft_skills": 1.0,
                "language_fit": 0.4,
            },
            fusion_config={
                "deterministic_weight": 0.35,
                "llm_weight": 0.65,
                "skill_gate": "removed",
                "cross_high": 80,
                "cross_low": 50,
            },
            changes_description=(
                "Graduated scoring: 8 root causes fixed. "
                "Binary threshold→graduated (0.45/0.60/0.80). "
                "Skill gate removed. Industry fuzzy match. "
                "Education dict expanded. Red flags halved. "
                "Depth keyword stuffing→JD coverage. "
                "Prompt fully rewritten for fair matching."
            ),
        )
        print(f"Created v2_graduated: {v2.id}")

        # ──────────────────────────────────────────
        # 2. MatchMaster v1 Benchmarks (old scores)
        # ──────────────────────────────────────────
        mm_shweta = await svc.import_matchmaster_eval(
            jd_id=JD_ID,
            resume_id="",
            candidate_name="Shweta Hugar",
            jd_title=JD_TITLE,
            jd_file_name=JD_FILE,
            resume_file_name="Shweta Hugar.pdf",
            overall_score=63.5,
            tier="D",
            source_version="v1_binary",
            scoring_version_id=v1.id,
            meta_summary="Experienced QA leader with 11+ years and hands-on automation architecture experience (Playwright, Selenium).",
        )
        print(f"MM Shweta: {mm_shweta.id}")

        mm_rajendra = await svc.import_matchmaster_eval(
            jd_id=JD_ID,
            resume_id="",
            candidate_name="Rajendra Kumar Bishoyi",
            jd_title=JD_TITLE,
            jd_file_name=JD_FILE,
            resume_file_name="Rajendra Kumar Bishoyi.pdf",
            overall_score=60.4,
            tier="D",
            source_version="v1_binary",
            scoring_version_id=v1.id,
            meta_summary="Strongly experienced SDET/automation engineer with 14.8 years and practical use of Selenium, Playwright.",
        )
        print(f"MM Rajendra: {mm_rajendra.id}")

        mm_shashikant = await svc.import_matchmaster_eval(
            jd_id=JD_ID,
            resume_id="",
            candidate_name="Shashikant Kumar",
            jd_title=JD_TITLE,
            jd_file_name=JD_FILE,
            resume_file_name="Shashikant Kumar.pdf",
            overall_score=64.3,
            tier="D",
            source_version="v1_binary",
            scoring_version_id=v1.id,
            meta_summary="Strong mid-senior QA engineer with 11+ years of hands-on automation in C#/.NET (Selenium, Playwright).",
        )
        print(f"MM Shashikant: {mm_shashikant.id}")

        # ──────────────────────────────────────────
        # 3. Gemini Benchmarks
        # ──────────────────────────────────────────
        gem_shweta = await svc.import_external_eval(
            source="gemini",
            source_version="gemini-2.5-pro",
            jd_id=JD_ID,
            candidate_name="Shweta Hugar",
            jd_title=JD_TITLE,
            overall_score=92,
            tier="A",
            dimension_scores={
                "team_positioning": "Best as lead/senior in mid-to-large QA team; ideal for Playwright+CI/CD architect role",
                "work_attitude": "Strong leadership, framework migration experience, proactive cross-tool adoption",
                "cross_team": "Evidence of API/WebSocket testing suggests backend collaboration; mentoring juniors",
                "self_discipline": "11+ years steady progression, framework-level contributions",
                "initiative": "Migrated Selenium→Playwright, adopted CI/CD pipeline design",
            },
            analysis_text=(
                "Shweta Hugar — Gemini Assessment (92/100)\n\n"
                "Core Strengths:\n"
                "- 11+ years QA automation, depth in Playwright + Selenium\n"
                "- Led framework migrations (Selenium→Playwright)\n"
                "- CI/CD pipeline design and implementation\n"
                "- API + WebSocket testing capability\n"
                "- Mentoring and team leadership experience\n\n"
                "Interview Focus:\n"
                "- How she manages framework migration risks in production\n"
                "- Her approach to mentoring junior QA engineers\n"
                "- Experience with industrial automation domain testing"
            ),
            strengths=[
                "11+ years automation with depth in Playwright + Selenium",
                "Led Selenium→Playwright framework migration",
                "CI/CD pipeline architect",
                "API and WebSocket testing",
                "Team leadership and mentoring",
            ],
            weaknesses=[
                "May need ramp-up on specific WITS domain tools",
                "Resume could be more metrics-driven",
            ],
        )
        print(f"Gemini Shweta: {gem_shweta.id}")

        gem_rajendra = await svc.import_external_eval(
            source="gemini",
            source_version="gemini-2.5-pro",
            jd_id=JD_ID,
            candidate_name="Rajendra Kumar Bishoyi",
            jd_title=JD_TITLE,
            overall_score=95,
            tier="A",
            dimension_scores={
                "team_positioning": "Senior/lead SDET; ideal for complex enterprise automation architecture",
                "work_attitude": "14.8 years continuous growth; API + UI + mobile automation across Azure DevOps",
                "cross_team": "Full-stack testing (API, UI, mobile, performance) = strong cross-team capability",
                "self_discipline": "Longest tenure 3+ years at multiple companies; steady career progression",
                "initiative": "Built BDD frameworks from scratch, Postman→RestAssured migration, mobile automation",
            },
            analysis_text=(
                "Rajendra Kumar Bishoyi — Gemini Assessment (95/100)\n\n"
                "Core Strengths:\n"
                "- 14.8 years covering Selenium, Playwright, Appium, RestAssured\n"
                "- Built BDD frameworks from scratch\n"
                "- Full-stack testing: API + UI + mobile + performance\n"
                "- Azure DevOps CI/CD pipeline expertise\n"
                "- Enterprise domain experience (banking, logistics)\n\n"
                "Interview Focus:\n"
                "- Deep dive into his BDD framework architecture decisions\n"
                "- How he handles mobile vs web test strategy\n"
                "- Experience leading automation roadmap"
            ),
            strengths=[
                "14.8 years breadth: Selenium, Playwright, Appium, RestAssured",
                "Built BDD frameworks from scratch",
                "Full-stack testing capability (API + UI + mobile + performance)",
                "Azure DevOps CI/CD expertise",
                "Enterprise domain experience",
            ],
            weaknesses=[
                "Many tools listed — need to verify depth vs breadth",
                "C# experience not explicit (Java + Python primary)",
            ],
        )
        print(f"Gemini Rajendra: {gem_rajendra.id}")

        gem_shashikant = await svc.import_external_eval(
            source="gemini",
            source_version="gemini-2.5-pro",
            jd_id=JD_ID,
            candidate_name="Shashikant Kumar",
            jd_title=JD_TITLE,
            overall_score=85,
            tier="B",
            dimension_scores={
                "team_positioning": "Mid-to-senior QA engineer; strong hands-on C#/.NET automation",
                "work_attitude": "11+ years consistent QA work; Selenium + Playwright in C#",
                "cross_team": "Some API testing evidence; primarily UI automation focused",
                "self_discipline": "Steady progression, no major gaps",
                "initiative": "C# framework adoption, some CI/CD work",
            },
            analysis_text=(
                "Shashikant Kumar — Gemini Assessment (85/100)\n\n"
                "Core Strengths:\n"
                "- 11+ years in QA automation\n"
                "- Strong C#/.NET + Selenium + Playwright\n"
                "- Matches WITS tech stack well (C# required)\n\n"
                "Interview Focus:\n"
                "- C# framework design decisions\n"
                "- How he approaches test architecture vs just writing tests\n"
                "- Experience with CI/CD pipeline ownership"
            ),
            strengths=[
                "11+ years QA automation experience",
                "Strong C#/.NET alignment with JD requirement",
                "Selenium + Playwright hands-on",
            ],
            weaknesses=[
                "Less breadth compared to other candidates",
                "API testing depth unclear",
                "Leadership/mentoring evidence limited",
            ],
        )
        print(f"Gemini Shashikant: {gem_shashikant.id}")

        # ──────────────────────────────────────────
        # 4. Cross-model Comparisons
        # ──────────────────────────────────────────
        cmp1 = await svc.create_cross_comparison(
            benchmark_a_id=mm_shweta.id,
            benchmark_b_id=gem_shweta.id,
            comparison_text=(
                "Shweta Hugar: MatchMaster 63.5/D vs Gemini 92/A\n\n"
                "Root Cause of Gap:\n"
                "1. MatchMaster binary skill matching: NUnit≠JUnit→0 credit (cosine ~0.73)\n"
                "2. Skill gate hard cap: skill_match<30 → final capped at 69\n"
                "3. Depth analyzer penalized JD skill coverage as 'keyword stuffing'\n"
                "4. LLM prompt anchored to audit mode, penalized concise resume style\n\n"
                "Gemini Approach:\n"
                "- Recognized tool equivalence (Playwright≈Selenium≈Cypress)\n"
                "- Valued framework migration experience (Selenium→Playwright)\n"
                "- Credited leadership evidence (mentoring, architecture)\n"
                "- Fair career trajectory assessment"
            ),
            key_differences=[
                "Skill matching: binary vs graduated",
                "Skill gate: hard cap at 69 vs none",
                "Tool equivalence recognition",
                "Leadership value assessment",
                "Resume style fairness",
            ],
            preferred_source="gemini",
            accuracy_notes="Gemini's assessment more aligned with real-world fit. MatchMaster v1 systematically undercounted.",
            compared_by="user",
        )
        print(f"Comparison Shweta: {cmp1.id}")

        cmp2 = await svc.create_cross_comparison(
            benchmark_a_id=mm_rajendra.id,
            benchmark_b_id=gem_rajendra.id,
            comparison_text=(
                "Rajendra Kumar Bishoyi: MatchMaster 60.4/D vs Gemini 95/A\n\n"
                "Root Cause of Gap:\n"
                "1. Same binary skill matching issues\n"
                "2. Industry match: exact string 'automation testing' ≠ 'banking'/'logistics'\n"
                "3. Experience calc: relevant_industry_ratio = 0 despite 14.8 years\n"
                "4. Depth analyzer flagged broad skill coverage as stuffing\n\n"
                "Gemini Approach:\n"
                "- Valued breadth (Selenium+Playwright+Appium+RestAssured) as strength\n"
                "- Recognized BDD framework architecture as deep expertise\n"
                "- Credited enterprise domain experience as transferable\n"
                "- Full-stack testing capability = high value for senior role"
            ),
            key_differences=[
                "Industry matching: exact vs fuzzy",
                "Breadth treated as strength vs stuffing",
                "BDD framework architecture recognition",
                "Enterprise domain transferability",
            ],
            preferred_source="gemini",
            accuracy_notes="Rajendra has the most experience (14.8y) and broadest skill set. MatchMaster v1 penalized breadth.",
            compared_by="user",
        )
        print(f"Comparison Rajendra: {cmp2.id}")

        cmp3 = await svc.create_cross_comparison(
            benchmark_a_id=mm_shashikant.id,
            benchmark_b_id=gem_shashikant.id,
            comparison_text=(
                "Shashikant Kumar: MatchMaster 64.3/D vs Gemini 85/B\n\n"
                "Root Cause of Gap:\n"
                "1. Education matcher: B.E. not in dictionary → degree_level=0\n"
                "2. Skill matching binary cliff for C# tools\n"
                "3. Red flag detector over-penalized normal 2-3yr tenure changes\n\n"
                "Gemini Approach:\n"
                "- C#/.NET directly matches JD requirement (competitive advantage)\n"
                "- Selenium + Playwright in C# = exact tech stack fit\n"
                "- Rated lower than other two (85 vs 92/95) — appropriate relative ranking\n"
                "- Noted limited leadership/mentoring evidence as genuine weakness"
            ),
            key_differences=[
                "Education recognition: B.E. mapping",
                "C# tech stack direct match valued",
                "Relative ranking preserved (lowest of 3)",
                "Red flag threshold calibration",
            ],
            preferred_source="gemini",
            accuracy_notes="Gemini correctly identified Shashikant as strong but relatively weaker than others. MatchMaster flattened all three to D.",
            compared_by="user",
        )
        print(f"Comparison Shashikant: {cmp3.id}")

        # ──────────────────────────────────────────
        # 5. Calibration Feedback (documenting the 8 fixes)
        # ──────────────────────────────────────────
        await svc.submit_feedback(
            scoring_version_id=v1.id,
            accuracy_rating=2,
            feedback_text=(
                "v1_binary systematic under-scoring: all 3 candidates scored D (60-64) vs Gemini's A/A/B (92/95/85). "
                "8 root causes identified:\n"
                "1. SkillMatcher binary cliff (0.75 threshold)\n"
                "2. SkillMatcher weight too high (2.0/7.0 = 28.6%)\n"
                "3. Score Fusion hard caps (skill<30→finalMax69)\n"
                "4. ExperienceCalculator exact industry match\n"
                "5. DepthAnalyzer penalized JD skill coverage as stuffing\n"
                "6. RedFlagDetector over-punishment\n"
                "7. LLM prompt anchored to audit/AI-detection mode\n"
                "8. EducationMatcher incomplete degree dictionary"
            ),
            action_taken=(
                "Created v2_graduated: graduated scoring (0.45/0.60/0.80), "
                "removed skill gate, fuzzy industry match, "
                "expanded education dict, halved red flag penalties, "
                "depth coverage instead of stuffing detection, "
                "prompt rewritten for fair matching, "
                "fusion weights 0.35/0.65"
            ),
        )
        print("Calibration feedback recorded.")

        print("\n✅ Seed complete.")


if __name__ == "__main__":
    asyncio.run(main())
