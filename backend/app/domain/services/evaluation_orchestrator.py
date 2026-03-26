"""Evaluation Orchestrator — coordinates the 3-stage pipeline."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel, Field, field_validator

from app.domain.entities.dimension_score import DeterministicScores, LLMDimensionScore, LLMScores
from app.domain.entities.evaluation import EvaluationResult, EvaluationStatus, TokenUsage
from app.domain.entities.job_description import ParsedJD
from app.domain.entities.resume import ParsedResume
from app.domain.scorers.career_progression import CareerProgressionScorer
from app.domain.scorers.depth_analyzer import DepthAnalyzer
from app.domain.scorers.education_matcher import EducationMatcher
from app.domain.scorers.experience_calc import ExperienceCalculator
from app.domain.scorers.keyword_overlap import KeywordOverlap
from app.domain.scorers.red_flag_detector import RedFlagDetector
from app.domain.scorers.skill_matcher import SkillMatcher
from app.domain.services.score_fusion import ScoreFusion
from app.infrastructure.cache.redis_cache import redis_cache
from app.infrastructure.embeddings.embedding_client import EmbeddingClient
from app.infrastructure.embeddings.skill_taxonomy import SkillTaxonomy
from app.infrastructure.llm.openai_client import OpenAIClient
from app.infrastructure.llm.token_estimator import estimate_cost

logger = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).resolve().parents[3] / "prompts"
_JD_CACHE_TTL = 7 * 24 * 3600  # 7 days
_RESUME_CACHE_TTL = 30 * 24 * 3600  # 30 days
_MAX_TEXT_CHARS = 50_000  # ~12,500 tokens — truncate beyond this to prevent OOM / token overflow


# ── Structured Output schemas for OpenAI ──

class JDExtractionOutput(BaseModel):
    title: str = ""
    company: str = ""
    department: str = ""
    location: str = ""
    employment_type: str = ""
    summary: str = ""
    must_have_skills: list[dict[str, Any]] = []
    nice_to_have_skills: list[dict[str, Any]] = []
    experience: dict[str, Any] = {}
    education: dict[str, Any] = {}
    responsibilities: list[str] = []
    keywords: list[str] = []
    language_requirements: list[str] = []
    soft_skill_keywords: list[str] = []


class ResumeExtractionOutput(BaseModel):
    candidate_name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    summary: str = ""
    skills: list[str] = []
    work_experiences: list[dict[str, Any]] = []
    education: list[dict[str, Any]] = []
    certifications: list[dict[str, Any]] = []
    languages: list[str] = []
    total_years_experience: float | None = None
    current_title: str = ""
    current_company: str = ""


class InterviewQuestionsOutput(BaseModel):
    behavioral: list[str] = Field(default_factory=list)
    technical: list[str] = Field(default_factory=list)


class ConsolidatedEvalOutput(BaseModel):
    technical_skills: dict[str, Any] = {}
    work_experience: dict[str, Any] = {}
    education: dict[str, Any] = {}
    career_trajectory: dict[str, Any] = {}
    red_flags: dict[str, Any] = {}
    soft_skills: dict[str, Any] = {}
    language_fit: dict[str, Any] = {}
    overall_score: float = 0.0
    meta_summary: str = ""
    interview_questions: InterviewQuestionsOutput = Field(default_factory=InterviewQuestionsOutput)
    strengths: list[str] = []
    weaknesses: list[str] = []

    @field_validator("interview_questions", mode="before")
    @classmethod
    def coerce_questions(cls, v: object) -> dict:
        """Accept new {behavioral, technical} dict or legacy flat list."""
        def _extract(lst: object) -> list[str]:
            if not isinstance(lst, list):
                return []
            result: list[str] = []
            for item in lst:
                if isinstance(item, str):
                    result.append(item)
                elif isinstance(item, dict):
                    text = item.get("q") or item.get("question") or item.get("text") or ""
                    if text:
                        result.append(str(text))
            return result

        if isinstance(v, dict):
            return {
                "behavioral": _extract(v.get("behavioral", [])),
                "technical": _extract(v.get("technical", [])),
            }
        # Legacy flat list → put all into technical
        return {"behavioral": [], "technical": _extract(v)}


class EvaluationOrchestrator:
    def __init__(self) -> None:
        self._llm = OpenAIClient()
        self._emb_client = EmbeddingClient(self._llm)
        self._taxonomy = SkillTaxonomy(self._emb_client)
        self._fusion = ScoreFusion()
        self._jinja = Environment(
            loader=FileSystemLoader(str(_PROMPTS_DIR)),
            autoescape=False,
        )

    # ──────────────────────────────────────────────
    # Stage 0 — Document Extraction
    # ──────────────────────────────────────────────

    async def extract_jd(self, raw_text: str) -> tuple[ParsedJD, TokenUsage]:
        """Parse JD via LLM with sha256 caching."""
        if len(raw_text) > _MAX_TEXT_CHARS:
            logger.warning("JD text truncated from %d to %d chars", len(raw_text), _MAX_TEXT_CHARS)
            raw_text = raw_text[:_MAX_TEXT_CHARS]

        cache_key = f"jd:{hashlib.sha256(raw_text.encode()).hexdigest()}"

        cached = await redis_cache.get(cache_key)
        if cached:
            return ParsedJD.model_validate(cached), TokenUsage()

        template = self._jinja.get_template("jd_extraction.jinja2")
        prompt = template.render(jd_text=raw_text)

        resp = await self._llm.chat(
            messages=[{"role": "user", "content": prompt}],
            response_format=JDExtractionOutput,
        )

        parsed = ParsedJD.model_validate(resp.parsed or {})
        await redis_cache.set(cache_key, parsed.model_dump(), ttl_seconds=_JD_CACHE_TTL)

        usage = TokenUsage(
            prompt_tokens=resp.prompt_tokens,
            completion_tokens=resp.completion_tokens,
            total_tokens=resp.total_tokens,
            estimated_cost_usd=estimate_cost(resp.prompt_tokens, resp.completion_tokens),
        )
        return parsed, usage

    async def extract_resume(self, raw_text: str) -> tuple[ParsedResume, TokenUsage]:
        """Parse resume via LLM with sha256 caching."""
        if len(raw_text) > _MAX_TEXT_CHARS:
            logger.warning("Resume text truncated from %d to %d chars", len(raw_text), _MAX_TEXT_CHARS)
            raw_text = raw_text[:_MAX_TEXT_CHARS]

        cache_key = f"resume:{hashlib.sha256(raw_text.encode()).hexdigest()}"

        cached = await redis_cache.get(cache_key)
        if cached:
            return ParsedResume.model_validate(cached), TokenUsage()

        template = self._jinja.get_template("resume_extraction.jinja2")
        prompt = template.render(resume_text=raw_text)

        resp = await self._llm.chat(
            messages=[{"role": "user", "content": prompt}],
            response_format=ResumeExtractionOutput,
        )

        parsed = ParsedResume.model_validate(resp.parsed or {})
        await redis_cache.set(cache_key, parsed.model_dump(), ttl_seconds=_RESUME_CACHE_TTL)

        usage = TokenUsage(
            prompt_tokens=resp.prompt_tokens,
            completion_tokens=resp.completion_tokens,
            total_tokens=resp.total_tokens,
            estimated_cost_usd=estimate_cost(resp.prompt_tokens, resp.completion_tokens),
        )
        return parsed, usage

    # ──────────────────────────────────────────────
    # Stage 1 — Deterministic Pre-Score (NO LLM)
    # ──────────────────────────────────────────────

    async def run_deterministic(
        self, jd: ParsedJD, resume: ParsedResume
    ) -> DeterministicScores:
        skill_matcher = SkillMatcher(self._taxonomy)
        exp_calc = ExperienceCalculator()
        edu_matcher = EducationMatcher()
        kw_overlap = KeywordOverlap()
        red_flag = RedFlagDetector()
        depth = DepthAnalyzer()
        career = CareerProgressionScorer()

        skill_r, exp_r, edu_r, kw_r, rf_r, depth_r, career_r = await asyncio.gather(
            skill_matcher.score(jd, resume),
            exp_calc.score(jd, resume),
            edu_matcher.score(jd, resume),
            kw_overlap.score(jd, resume),
            red_flag.score(jd, resume),
            depth.score(jd, resume),
            career.score(jd, resume),
        )

        return DeterministicScores(
            skill_match=skill_r,
            experience=exp_r,
            education=edu_r,
            keyword_overlap=kw_r,
            red_flags=rf_r,
            depth_analysis=depth_r,
            career_progression=career_r,
        )

    # ──────────────────────────────────────────────
    # Stage 2 — LLM Deep Evaluation (1 consolidated call)
    # ──────────────────────────────────────────────

    async def run_llm_evaluation(
        self,
        jd: ParsedJD,
        resume: ParsedResume,
        det_scores: DeterministicScores,
    ) -> tuple[LLMScores, TokenUsage]:
        template = self._jinja.get_template("consolidated_eval.jinja2")
        prompt = template.render(
            jd=jd.model_dump(),
            resume=resume.model_dump(),
            deterministic=det_scores.model_dump(),
        )

        resp = await self._llm.chat(
            messages=[{"role": "user", "content": prompt}],
            response_format=ConsolidatedEvalOutput,
        )

        if resp.parsed is None:
            raise ValueError(
                f"LLM response could not be parsed as valid JSON/schema. "
                f"Raw content (first 400 chars): {resp.content[:400]!r}"
            )
        data = resp.parsed

        def _to_dim(d: dict, name: str) -> LLMDimensionScore:
            score = d.get("score")
            if score is None or not isinstance(score, (int, float)):
                logger.warning("LLM dimension '%s' missing or invalid score, defaulting to 50", name)
                score = 50.0
            score = max(0.0, min(100.0, float(score)))
            return LLMDimensionScore(
                dimension=name,
                score=score,
                reasoning=d.get("reasoning", ""),
                evidence=d.get("evidence", []),
            )

        llm_scores = LLMScores(
            technical_skills=_to_dim(data.get("technical_skills", {}), "technical_skills"),
            work_experience=_to_dim(data.get("work_experience", {}), "work_experience"),
            education=_to_dim(data.get("education", {}), "education"),
            career_trajectory=_to_dim(data.get("career_trajectory", {}), "career_trajectory"),
            red_flags=_to_dim(data.get("red_flags", {}), "red_flags"),
            soft_skills=_to_dim(data.get("soft_skills", {}), "soft_skills"),
            language_fit=_to_dim(data.get("language_fit", {}), "language_fit"),
            overall_score=data.get("overall_score", 0),
            meta_summary=data.get("meta_summary", ""),
            interview_questions=data.get("interview_questions", []),
            strengths=data.get("strengths", []),
            weaknesses=data.get("weaknesses", []),
        )

        usage = TokenUsage(
            prompt_tokens=resp.prompt_tokens,
            completion_tokens=resp.completion_tokens,
            total_tokens=resp.total_tokens,
            estimated_cost_usd=estimate_cost(resp.prompt_tokens, resp.completion_tokens),
        )
        return llm_scores, usage

    # ──────────────────────────────────────────────
    # Full pipeline
    # ──────────────────────────────────────────────

    async def evaluate(
        self,
        jd_raw_text: str,
        resume_raw_text: str,
        status_callback=None,
    ) -> EvaluationResult:
        """Run the complete 3-stage evaluation pipeline."""
        start = time.time()
        total_usage = TokenUsage()
        result = EvaluationResult()

        def _add_usage(u: TokenUsage) -> None:
            total_usage.prompt_tokens += u.prompt_tokens
            total_usage.completion_tokens += u.completion_tokens
            total_usage.total_tokens += u.total_tokens
            total_usage.estimated_cost_usd += u.estimated_cost_usd

        try:
            # Stage 0: Parse docs
            if status_callback:
                await status_callback(EvaluationStatus.PARSING)
            result.status = EvaluationStatus.PARSING

            (parsed_jd, jd_usage), (parsed_resume, resume_usage) = await asyncio.gather(
                self.extract_jd(jd_raw_text),
                self.extract_resume(resume_raw_text),
            )
            _add_usage(jd_usage)
            _add_usage(resume_usage)

            # Stage 1: Deterministic scoring
            if status_callback:
                await status_callback(EvaluationStatus.SCORING_DETERMINISTIC)
            result.status = EvaluationStatus.SCORING_DETERMINISTIC

            det_scores = await self.run_deterministic(parsed_jd, parsed_resume)
            result.deterministic_scores = det_scores

            # Stage 2: LLM evaluation
            if status_callback:
                await status_callback(EvaluationStatus.SCORING_LLM)
            result.status = EvaluationStatus.SCORING_LLM

            llm_scores, llm_usage = await self.run_llm_evaluation(
                parsed_jd, parsed_resume, det_scores
            )
            _add_usage(llm_usage)
            result.llm_scores = llm_scores

            # Stage 3: Fusion
            if status_callback:
                await status_callback(EvaluationStatus.FUSING)
            result.status = EvaluationStatus.FUSING

            final_score, confidence, tier = self._fusion.fuse(det_scores, llm_scores)
            result.final_score = final_score
            result.confidence = confidence
            result.tier = tier
            result.meta_summary = llm_scores.meta_summary
            result.interview_questions = llm_scores.interview_questions
            result.token_usage = total_usage
            result.processing_time_ms = int((time.time() - start) * 1000)
            result.status = EvaluationStatus.COMPLETED

        except Exception as e:
            logger.exception("Evaluation failed")
            result.status = EvaluationStatus.FAILED
            result.processing_time_ms = int((time.time() - start) * 1000)
            raise

        return result
