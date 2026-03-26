"""Abstract base for deterministic scorers."""

from __future__ import annotations

import abc

from app.domain.entities.dimension_score import DimensionScore
from app.domain.entities.job_description import ParsedJD
from app.domain.entities.resume import ParsedResume


class BaseScorer(abc.ABC):
    """Base class for all Stage-1 deterministic scorers."""

    dimension: str = ""

    @abc.abstractmethod
    async def score(self, jd: ParsedJD, resume: ParsedResume) -> DimensionScore:
        ...
