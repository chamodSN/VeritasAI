from __future__ import annotations

import io
import time

import pdfplumber

from core.logging import logger
from agents.summarization import SummarizationAgent
from agents.issue_extractor import IssueExtractorAgent, _parse_issues
from agents.argument import ArgumentAgent
from agents.citation import CitationAgent, _parse_citation_result, verify_with_courtlistener, _recount
from core.models import CitationVerificationResult


def extract_text_from_pdf(file_bytes: bytes) -> str:
    text_parts: list[str] = []
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages[:40]:  # cap pages for cost control
                page_text = page.extract_text() or ""
                if page_text.strip():
                    text_parts.append(page_text)
    except Exception as exc:
        logger.error("pdf_extraction_failed", error=str(exc))
        return ""

    return "\n\n".join(text_parts)


class _FakeCase:
    """Minimal shim so PDF text can be summarized using the existing agent
    prompts, which expect case-like objects with case_name/court/date_filed/full_text."""

    def __init__(self, name: str, text: str) -> None:
        self.case_name = name
        self.court = "Uploaded document"
        self.date_filed = ""
        self.precedential = True
        self.citation_count = 0
        self.snippet = text[:400]
        self.full_text = text


async def analyze_pdf_text(text: str, user_id: str | None = None, filename: str = "document.pdf") -> dict:
    start = time.monotonic()
    fake_case = _FakeCase(filename, text)

    query = f"Analysis of uploaded document: {filename}"
    state = {
        "query": query,
        "cases": [fake_case],
        "user_id": user_id,
    }

    summary = await SummarizationAgent().run(state)
    state["summary"] = summary

    raw_issues = await IssueExtractorAgent().run(state)
    issues = _parse_issues(raw_issues)
    state["issues"] = issues

    arguments = await ArgumentAgent().run(state)
    state["arguments"] = arguments

    raw_citations = await CitationAgent().run(state)
    citation_result = _parse_citation_result(raw_citations)
    if citation_result.citations:
        verified = await verify_with_courtlistener(citation_result.citations)
        citation_result = _recount(CitationVerificationResult(
            total=citation_result.total,
            valid=citation_result.valid,
            invalid=citation_result.invalid,
            needs_review=citation_result.needs_review,
            citations=verified,
        ))

    elapsed = round(time.monotonic() - start, 2)

    return {
        "query": query,
        "summary": summary,
        "issues": issues,
        "arguments": arguments,
        "citation_verification": {
            "total": citation_result.total,
            "valid": citation_result.valid,
            "invalid": citation_result.invalid,
            "needs_review": citation_result.needs_review,
            "citations": [c.__dict__ for c in citation_result.citations],
        },
        "divergences": [],
        "outcome_prediction": {},
        "judge_profiles": [],
        "source_cases": [],
        "cases_analyzed": 0,
        "processing_time_seconds": elapsed,
        "prior_context": False,
    }
