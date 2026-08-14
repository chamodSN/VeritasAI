from __future__ import annotations

from typing import Any, Optional, TypedDict

from core.models import CitationVerificationResult
from services.courtlistener import CaseResult
from services.judge_intelligence import JudgeProfile


class AnalysisState(TypedDict, total=False):
    # Input
    query: str
    user_id: Optional[str]
    request_id: Optional[str]
    prior_context: Optional[str]

    # Retrieved data
    cases: list[CaseResult]
    judge_profiles: list[JudgeProfile]

    # Agent outputs
    summary: str
    issues: list[str]
    arguments: str
    citation_verification: CitationVerificationResult
    divergences: list[dict[str, Any]]
    outcome_prediction: dict[str, Any]
    judge_analysis: str
    analytics: str

    # Meta
    cases_analyzed: int
    processing_time_seconds: float
