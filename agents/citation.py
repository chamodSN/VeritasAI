
from __future__ import annotations
import json
import re
from typing import Any

from agents.base_agent import BaseAgent
from core.models import CitationAnalysis, CitationStatus, CitationVerificationResult, ConfidenceLevel
from core.logging import logger
from graph.state import AnalysisState
from services.courtlistener import courtlistener_client


class CitationAgent(BaseAgent):

    @property
    def system_prompt(self) -> str:
        return (
            "You are a legal citation verification specialist with expertise in Bluebook format. "
            "Extract all legal citations from the provided text and verify each one. "
            "For each citation assess: format compliance, logical consistency, and authenticity. "
            "Return ONLY a JSON object with this exact structure:\n"
            "{\n"
            '  "citations": [\n'
            '    {\n'
            '      "citation": "full citation text",\n'
            '      "status": "VALID"|"INVALID"|"NEEDS_REVIEW",\n'
            '      "confidence": "HIGH"|"MEDIUM"|"LOW",\n'
            '      "issues": "description or null",\n'
            '      "recommendations": "correction or null"\n'
            "    }\n"
            "  ]\n"
            "}"
        )

    def format_user_message(self, state: dict[str, Any]) -> str:
        summary = state.get("summary", "")
        arguments = state.get("arguments", "")
        return (
            f"Extract and verify all legal citations from the following text:\n\n"
            f"SUMMARY:\n{summary[:2000]}\n\n"
            f"ARGUMENTS:\n{arguments[:2000]}"
        )


def _parse_citation_result(raw: str) -> CitationVerificationResult:
    """Parse LLM JSON output into CitationVerificationResult."""
    try:
        cleaned = re.sub(r"```(?:json)?\s*|\s*```", "", raw).strip()
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if not match:
            return CitationVerificationResult(total=0, valid=0, invalid=0, needs_review=0)

        data = json.loads(match.group())
        citations_raw = data.get("citations", [])

        citations: list[CitationAnalysis] = []
        valid = invalid = needs_review = 0

        for c in citations_raw:
            status_str = c.get("status", "NEEDS_REVIEW")
            try:
                status = CitationStatus(status_str)
            except ValueError:
                status = CitationStatus.NEEDS_REVIEW

            if status == CitationStatus.VALID:
                valid += 1
            elif status == CitationStatus.INVALID:
                invalid += 1
            else:
                needs_review += 1

            confidence_str = c.get("confidence", "MEDIUM")
            try:
                confidence = ConfidenceLevel(confidence_str)
            except ValueError:
                confidence = ConfidenceLevel.MEDIUM

            citations.append(CitationAnalysis(
                citation=c.get("citation", ""),
                status=status,
                confidence=confidence,
                issues=c.get("issues") or None,
                recommendations=c.get("recommendations") or None,
            ))

        return CitationVerificationResult(
            total=len(citations), valid=valid, invalid=invalid,
            needs_review=needs_review, citations=citations,
        )

    except Exception as exc:
        logger.warning("citation_parse_failed", error=str(exc))
        return CitationVerificationResult(total=0, valid=0, invalid=0, needs_review=0)


async def verify_with_courtlistener(citations: list[CitationAnalysis]) -> list[CitationAnalysis]:
    """
    Cross-check LLM-identified citations against CourtListener's Citation
    Lookup API. Downgrades citations the LLM marked VALID but that don't
    exist in CourtListener's database — a strong hallucination signal.
    """
    verified: list[CitationAnalysis] = []
    for c in citations:
        if c.status != CitationStatus.VALID:
            verified.append(c)
            continue

        result = await courtlistener_client.lookup_citation(c.citation)
        if result is None:
            c = CitationAnalysis(
                citation=c.citation,
                status=CitationStatus.NEEDS_REVIEW,
                confidence=ConfidenceLevel.LOW,
                issues="Citation not found in CourtListener database — may be hallucinated",
                recommendations="Manually verify this citation before use",
            )
        verified.append(c)
    return verified


def _recount(result: CitationVerificationResult) -> CitationVerificationResult:
    """Recompute valid/invalid/needs_review counts after the hallucination guard."""
    valid = sum(1 for c in result.citations if c.status == CitationStatus.VALID)
    invalid = sum(1 for c in result.citations if c.status == CitationStatus.INVALID)
    needs_review = sum(1 for c in result.citations if c.status == CitationStatus.NEEDS_REVIEW)
    return CitationVerificationResult(
        total=len(result.citations), valid=valid, invalid=invalid,
        needs_review=needs_review, citations=result.citations,
    )


async def citation_node(state: AnalysisState) -> AnalysisState:
    agent = CitationAgent()
    raw = await agent.run(state)
    result = _parse_citation_result(raw)

    if result.citations:
        verified_citations = await verify_with_courtlistener(result.citations)
        result = _recount(CitationVerificationResult(
            total=result.total, valid=result.valid, invalid=result.invalid,
            needs_review=result.needs_review, citations=verified_citations,
        ))

    return {**state, "citation_verification": result}