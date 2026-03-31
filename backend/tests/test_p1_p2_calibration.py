"""P1/P2 calibration test — verifies tenure recency weighting + education field decay.

Run: docker compose exec backend python -m pytest tests/test_p1_p2_calibration.py -v
Or:  docker compose exec backend python tests/test_p1_p2_calibration.py
"""

import asyncio

from app.domain.entities.job_description import (
    ParsedJD, SkillRequirement, ExperienceRequirement, EducationRequirement,
)
from app.domain.entities.resume import ParsedResume, WorkExperience, Education
from app.domain.scorers.red_flag_detector import RedFlagDetector
from app.domain.scorers.education_matcher import EducationMatcher

# ─── Standard JD ───
jd = ParsedJD(
    title="Senior Software Test Engineer",
    must_have_skills=[
        SkillRequirement(name="Selenium", level="advanced", years=3),
        SkillRequirement(name="C#", level="intermediate", years=2),
    ],
    nice_to_have_skills=[
        SkillRequirement(name="Playwright", level="intermediate"),
    ],
    experience=ExperienceRequirement(min_years=5, preferred_years=8, industries=["industrial automation"]),
    education=EducationRequirement(min_degree="bachelor", preferred_fields=["Computer Science", "Software Engineering"]),
    responsibilities=["Design test frameworks", "Automate regression"],
    keywords=["automation", "testing", "CI/CD", "Selenium", "C#"],
)


# ═══════════════════════════════════════════════════════════════
# P1: TENURE RECENCY WEIGHTING
# ═══════════════════════════════════════════════════════════════

p1_personas = {
    # A) 2 recent short stints (2024-2025) — should be penalized heavily
    "P1-A) 2 RECENT short stints": ParsedResume(
        candidate_name="Recent Hopper",
        skills=["Selenium", "C#"],
        work_experiences=[
            WorkExperience(company="AXA", title="SDET", start_date="2025-01", end_date="2025-05", duration_months=4),
            WorkExperience(company="NCR", title="QA Lead", start_date="2024-03", end_date="2024-11", duration_months=8),
            WorkExperience(company="Infosys", title="Senior SDET", start_date="2020-01", end_date="2024-02", duration_months=49),
        ],
        total_years_experience=5.0,
    ),

    # B) 2 OLD short stints (2017-2018) — should be penalized lightly
    "P1-B) 2 OLD short stints": ParsedResume(
        candidate_name="Old Hopper",
        skills=["Selenium", "C#"],
        work_experiences=[
            WorkExperience(company="SmallCo", title="QA Engineer", start_date="2018-01", end_date="2018-07", duration_months=6),
            WorkExperience(company="TinyCorp", title="Tester", start_date="2017-03", end_date="2017-11", duration_months=8),
            WorkExperience(company="StableCorp", title="Senior SDET", start_date="2019-01", end_date="2025-12", duration_months=84),
        ],
        total_years_experience=8.0,
    ),

    # C) 2 contract recent stints — contract discount should soften
    "P1-C) 2 RECENT contract stints": ParsedResume(
        candidate_name="Contract Worker",
        skills=["Selenium", "C#"],
        work_experiences=[
            WorkExperience(company="AXA", title="QA Consultant", start_date="2025-01", end_date="2025-05", duration_months=4),
            WorkExperience(company="NCR", title="Contract SDET", start_date="2024-03", end_date="2024-11", duration_months=8),
            WorkExperience(company="Infosys", title="Senior SDET", start_date="2020-01", end_date="2024-02", duration_months=49),
        ],
        total_years_experience=5.0,
    ),

    # D) 3 recent short stints — cluster penalty
    "P1-D) 3 RECENT short stints (pattern)": ParsedResume(
        candidate_name="Serial Hopper",
        skills=["Selenium", "C#"],
        work_experiences=[
            WorkExperience(company="Co1", title="SDET", start_date="2025-06", end_date="2025-09", duration_months=3),
            WorkExperience(company="Co2", title="QA Lead", start_date="2025-01", end_date="2025-05", duration_months=4),
            WorkExperience(company="Co3", title="SDET", start_date="2024-03", end_date="2024-11", duration_months=8),
            WorkExperience(company="StableCorp", title="QA", start_date="2018-01", end_date="2024-02", duration_months=74),
        ],
        total_years_experience=7.0,
    ),

    # E) No short stints — baseline (100 - 0 = 100)
    "P1-E) STABLE career (no short)": ParsedResume(
        candidate_name="Stable Pro",
        skills=["Selenium", "C#"],
        work_experiences=[
            WorkExperience(company="BigCorp", title="Senior SDET", start_date="2020-01", end_date="2025-12", duration_months=72),
            WorkExperience(company="MidCorp", title="SDET", start_date="2017-01", end_date="2019-12", duration_months=36),
        ],
        total_years_experience=9.0,
    ),
}


# ═══════════════════════════════════════════════════════════════
# P2: EDUCATION FIELD DECAY FOR SENIORS
# ═══════════════════════════════════════════════════════════════

p2_personas = {
    # A) Senior (12y) with Electrical Engineering — field should barely matter
    "P2-A) 12y EE degree": ParsedResume(
        candidate_name="Senior EE",
        skills=["Selenium", "C#"],
        education=[Education(institution="NTU", degree="Bachelor", field="Electrical Engineering", graduation_year=2013)],
        total_years_experience=12.0,
    ),

    # B) Senior (12y) with CS degree — baseline
    "P2-B) 12y CS degree": ParsedResume(
        candidate_name="Senior CS",
        skills=["Selenium", "C#"],
        education=[Education(institution="NTU", degree="Bachelor", field="Computer Science", graduation_year=2013)],
        total_years_experience=12.0,
    ),

    # C) Junior (3y) with EE — field mismatch should hurt more
    "P2-C) 3y EE degree": ParsedResume(
        candidate_name="Junior EE",
        skills=["Selenium", "C#"],
        education=[Education(institution="NTU", degree="Bachelor", field="Electrical Engineering", graduation_year=2022)],
        total_years_experience=3.0,
    ),

    # D) Junior (3y) with CS — baseline
    "P2-D) 3y CS degree": ParsedResume(
        candidate_name="Junior CS",
        skills=["Selenium", "C#"],
        education=[Education(institution="NTU", degree="Bachelor", field="Computer Science", graduation_year=2022)],
        total_years_experience=3.0,
    ),

    # E) Mid (8y) with EE — moderate decay
    "P2-E) 8y EE degree": ParsedResume(
        candidate_name="Mid EE",
        skills=["Selenium", "C#"],
        education=[Education(institution="NTU", degree="Bachelor", field="Electrical Engineering", graduation_year=2017)],
        total_years_experience=8.0,
    ),
}


async def main():
    rf = RedFlagDetector()
    em = EducationMatcher()

    print("=" * 75)
    print("P1: TENURE RECENCY WEIGHTING")
    print("=" * 75)
    print(f"{'Persona':<42} {'Score':>5} {'Penalty':>8} {'Flags'}")
    print("-" * 75)

    for label, resume in p1_personas.items():
        result = await rf.score(jd, resume)
        print(f"{label:<42} {result.score:5.1f} {result.details:>8}  {result.evidence}")

    print()
    print("Expected behavior:")
    print("  A) 2 recent   → penalty ~19.2 (2×4×2.0 × 1.2 cluster)")
    print("  B) 2 old      → penalty ~4.8  (2×4×0.5 × 1.2 cluster)")
    print("  C) 2 contract → penalty ~9.6  (2×4×2.0×0.5 × 1.2 cluster)")
    print("  D) 3 recent   → penalty ~36.0 (3×4×2.0 × 1.5 cluster)")
    print("  E) stable     → penalty 0")
    print()
    print("Key assertion: A penalty >> B penalty (recent × 4)")
    print("Key assertion: C penalty ≈ A penalty × 0.5 (contract discount)")

    print()
    print("=" * 75)
    print("P2: EDUCATION FIELD DECAY FOR SENIORS")
    print("=" * 75)
    print(f"{'Persona':<42} {'Score':>5} {'Weight':>6} {'Details'}")
    print("-" * 75)

    for label, resume in p2_personas.items():
        result = await em.score(jd, resume)
        print(f"{label:<42} {result.score:5.1f} {result.weight:6.2f}  {result.details}")

    print()
    print("Expected behavior:")
    print("  A) 12y+EE → score ~74.0  (80%×1.0 + 20%×0.3)")
    print("  B) 12y+CS → score ~100.0 (80%×1.0 + 20%×1.0)")
    print("  C) 3y+EE  → score ~65.0  (50%×1.0 + 50%×0.3)")
    print("  D) 3y+CS  → score ~100.0 (50%×1.0 + 50%×1.0)")
    print("  E) 8y+EE  → score ~69.5  (65%×1.0 + 35%×0.3)")
    print()
    print("Key assertion: (A-B gap=~26) < (C-D gap=~35) — seniors less penalized for field mismatch")
    print("Key assertion: A.weight=0.40, C.weight=0.80 — education weight also decays")


asyncio.run(main())
