"""Scoring calibration test — 5 HR-realistic boundary personas."""

import asyncio

from app.domain.entities.job_description import (
    ParsedJD, SkillRequirement, ExperienceRequirement, EducationRequirement,
)
from app.domain.entities.resume import ParsedResume, WorkExperience, Education
from app.domain.entities.dimension_score import (
    DimensionScore, DeterministicScores, LLMScores, LLMDimensionScore,
)
from app.domain.scorers.red_flag_detector import RedFlagDetector
from app.domain.scorers.career_progression import CareerProgressionScorer
from app.domain.scorers.education_matcher import EducationMatcher
from app.domain.scorers.keyword_overlap import KeywordOverlap
from app.domain.scorers.experience_calc import ExperienceCalculator
from app.domain.scorers.depth_analyzer import DepthAnalyzer
from app.domain.services.score_fusion import ScoreFusion
from app.domain.services.evaluation_orchestrator import _resume_content_score

# Standard JD
jd = ParsedJD(
    title="Software Engineer",
    must_have_skills=[
        SkillRequirement(name="Python", level="advanced", years=3),
        SkillRequirement(name="SQL", level="intermediate", years=2),
    ],
    nice_to_have_skills=[
        SkillRequirement(name="Docker", level="intermediate"),
        SkillRequirement(name="AWS", level="beginner"),
    ],
    experience=ExperienceRequirement(min_years=3, preferred_years=5, industries=["technology"]),
    education=EducationRequirement(min_degree="bachelor", preferred_fields=["Computer Science"]),
    responsibilities=["Build APIs", "Design systems"],
    keywords=["API", "Python", "backend", "SQL", "cloud"],
)

personas = {
    "A) BLANK": ParsedResume(),

    "B) NAME-ONLY (OCR partial)": ParsedResume(
        candidate_name="Shubham Panigrahi",
    ),

    "C) FRESH GRAD (no exp)": ParsedResume(
        candidate_name="Jane Lin",
        summary="Recent CS graduate with internship experience",
        skills=["Python", "SQL", "Git"],
        education=[Education(institution="NTU", degree="Bachelor", field="Computer Science", graduation_year=2025)],
    ),

    "D) SINGLE-JOB JUNIOR (1yr)": ParsedResume(
        candidate_name="Tom Chen",
        summary="Junior developer with 1 year experience",
        skills=["Python", "JavaScript", "SQL", "Docker"],
        work_experiences=[
            WorkExperience(
                company="StartupCo", title="Software Engineer",
                start_date="2024-03", end_date="present", duration_months=12,
                industry="technology",
                description="Developed REST APIs using Python Flask. Managed PostgreSQL database. Deployed applications with Docker.",
                skills_used=["Python", "SQL", "Docker"],
            ),
        ],
        education=[Education(institution="NCKU", degree="Bachelor", field="Information Engineering", graduation_year=2024)],
        total_years_experience=1.0,
        current_title="Software Engineer",
    ),

    "E) SENIOR PERFECT MATCH": ParsedResume(
        candidate_name="Alex Wang",
        summary="Staff engineer, 10 years building high-scale Python services",
        skills=["Python", "SQL", "Docker", "AWS", "Kubernetes", "FastAPI", "PostgreSQL", "Redis"],
        work_experiences=[
            WorkExperience(
                company="BigTech", title="Staff Software Engineer",
                start_date="2021-01", end_date="present", duration_months=50,
                industry="technology",
                description="Architected microservice platform serving 5M+ daily users. Reduced latency by 60%. Led team of 8 engineers. Designed event-driven system processing 200K msgs/sec.",
                skills_used=["Python", "FastAPI", "Docker", "AWS", "Kubernetes"],
            ),
            WorkExperience(
                company="MidCorp", title="Senior Software Engineer",
                start_date="2018-04", end_date="2020-12", duration_months=33,
                industry="technology",
                description="Built data pipeline handling $2M daily transactions. Improved query performance by 40%. Mentored 3 junior developers.",
                skills_used=["Python", "SQL", "PostgreSQL", "Redis"],
            ),
            WorkExperience(
                company="WebStart", title="Software Engineer",
                start_date="2015-06", end_date="2018-03", duration_months=33,
                industry="technology",
                description="Developed RESTful APIs for e-commerce platform. Integrated payment gateway for 50K+ users.",
                skills_used=["Python", "Django", "SQL"],
            ),
        ],
        education=[Education(institution="NTU", degree="Master", field="Computer Science", graduation_year=2015)],
        total_years_experience=10.0,
        current_title="Staff Software Engineer",
    ),
}


async def main():
    fusion = ScoreFusion()

    header = f"{'Persona':<30} {'RF':>4} {'CP':>4} {'Edu':>4} {'KW':>4} {'Exp':>4} {'DA':>4} {'DetW':>6} {'CS':>4} {'Final':>6} {'Tier':>4}"
    print(header)
    print("-" * len(header))

    for label, resume in personas.items():
        rf = await RedFlagDetector().score(jd, resume)
        cp = await CareerProgressionScorer().score(jd, resume)
        em = await EducationMatcher().score(jd, resume)
        kw = await KeywordOverlap().score(jd, resume)
        ec = await ExperienceCalculator().score(jd, resume)
        da = await DepthAnalyzer().score(jd, resume)

        # Approximate skill_match (real one needs embeddings)
        sk_score = 0.0 if not resume.skills else 55.0
        sk = DimensionScore(dimension="skill_match", score=sk_score, weight=1.5)

        det = DeterministicScores(
            skill_match=sk, experience=ec, education=em,
            keyword_overlap=kw, red_flags=rf,
            depth_analysis=da, career_progression=cp,
        )
        det_avg = det.weighted_average
        cs = _resume_content_score(resume)

        # Realistic LLM score approximation per persona level
        # Fresh grad: LLM sees no experience → low scores. Senior: LLM sees rich content → high scores.
        llm_profiles = {
            0.0:  (0, 0),       # blank → LLM gets nothing
            0.2:  (5, 20),      # name only → LLM can barely assess
            0.6:  (25, 50),     # some content (fresh grad) → partial assessment
            0.8:  (25, 50),     # same tier
            1.0:  (50, 75),     # full content → normal assessment
        }
        base_lo, base_hi = llm_profiles.get(cs, (30, 60))
        # Use midpoint; seniors naturally have richer content that pushes higher
        has_rich_exp = len(resume.work_experiences) >= 3
        llm_base = base_hi if has_rich_exp else base_lo

        llm = LLMScores(
            technical_skills=LLMDimensionScore(dimension="technical_skills", score=llm_base),
            work_experience=LLMDimensionScore(dimension="work_experience", score=llm_base * 0.8 if not resume.work_experiences else llm_base),
            education=LLMDimensionScore(dimension="education", score=min(llm_base + 20, 100) if resume.education else llm_base),
            career_trajectory=LLMDimensionScore(dimension="career_trajectory", score=llm_base * 0.7 if len(resume.work_experiences) <= 1 else llm_base),
            red_flags=LLMDimensionScore(dimension="red_flags", score=max(llm_base, 30) if resume.work_experiences else 10),
            soft_skills=LLMDimensionScore(dimension="soft_skills", score=llm_base),
            language_fit=LLMDimensionScore(dimension="language_fit", score=llm_base),
        )

        final, conf, tier = fusion.fuse(det, llm, cs)
        print(
            f"{label:<30} {rf.score:4.0f} {cp.score:4.0f} {em.score:4.0f} "
            f"{kw.score:4.0f} {ec.score:4.0f} {da.score:4.0f} "
            f"{det_avg:6.1f} {cs:4.2f} {final:6.1f} {tier.value:>4}"
        )

    print()
    print("Expected ranges (Det = deterministic only, Final = fused with simulated LLM):")
    print("  A) BLANK          → Det ~0,  Final 0-5   (F)   unreadable")
    print("  B) NAME-ONLY      → Det ~5,  Final 5-15  (F)   OCR partial")
    print("  C) FRESH GRAD     → Det ~35, Final 25-40 (F)   degree+skills, no exp")
    print("  D) SINGLE-JOB JR  → Det ~55, Final 40-55 (F/D) some exp, below requirements")
    print("  E) SENIOR MATCH   → Det ~80, Final 70-85 (C/B) strong match")


asyncio.run(main())
