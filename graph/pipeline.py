# Path: graph/pipeline.py
from __future__ import annotations

import time
from typing import Any

from langgraph.graph import StateGraph, END

from core.logging import logger
from graph.state import AnalysisState
from services.courtlistener import courtlistener_client
from services.judge_intelligence import fetch_judge_profiles

from agents.summarization import summarization_node
from agents.issue_extractor import issue_extractor_node
from agents.argument import argument_node
from agents.citation import citation_node
from agents.analytics import analytics_node
from agents.judge_analysis import judge_analysis_node
from agents.divergence import divergence_node
from agents.outcome_predictor import outcome_predictor_node


async def fetch_cases_node(state: AnalysisState) -> AnalysisState:
    query = state["query"]
    async with courtlistener_client as cl:
        cases = await cl.search_cases(query, max_results=10)
        cases = await cl.enrich_cases_with_text(cases)
    logger.info("fetch_cases_completed", count=len(cases))
    return {**state, "cases": cases, "cases_analyzed": len(cases)}


async def judge_intelligence_node(state: AnalysisState) -> AnalysisState:
    cases = state.get("cases", [])
    profiles = await fetch_judge_profiles(cases)
    return {**state, "judge_profiles": profiles}


def build_pipeline() -> Any:
    graph = StateGraph(AnalysisState)

    graph.add_node("fetch_cases", fetch_cases_node)
    graph.add_node("judge_intelligence", judge_intelligence_node)
    graph.add_node("summarize", summarization_node)
    graph.add_node("extract_issues", issue_extractor_node)
    graph.add_node("generate_arguments", argument_node)
    graph.add_node("divergence", divergence_node)
    graph.add_node("outcome_predictor", outcome_predictor_node)
    graph.add_node("verify_citations", citation_node)
    graph.add_node("judge_analysis", judge_analysis_node)
    graph.add_node("analytics", analytics_node)

    graph.set_entry_point("fetch_cases")
    graph.add_edge("fetch_cases", "judge_intelligence")
    graph.add_edge("judge_intelligence", "summarize")
    graph.add_edge("summarize", "extract_issues")
    graph.add_edge("extract_issues", "generate_arguments")
    graph.add_edge("generate_arguments", "divergence")
    graph.add_edge("divergence", "outcome_predictor")
    graph.add_edge("outcome_predictor", "verify_citations")
    graph.add_edge("verify_citations", "judge_analysis")
    graph.add_edge("judge_analysis", "analytics")
    graph.add_edge("analytics", END)

    return graph.compile()


_compiled_pipeline = None


def get_pipeline():
    global _compiled_pipeline
    if _compiled_pipeline is None:
        _compiled_pipeline = build_pipeline()
    return _compiled_pipeline


async def run_pipeline(query: str, user_id: str | None = None, request_id: str | None = None,
                       prior_context: str | None = None) -> dict:
    start = time.monotonic()
    pipeline = get_pipeline()

    initial_state: AnalysisState = {
        "query": query,
        "user_id": user_id,
        "request_id": request_id,
        "prior_context": prior_context,
    }

    final_state = await pipeline.ainvoke(initial_state)
    elapsed = round(time.monotonic() - start, 2)

    cases = final_state.get("cases", [])
    return {
        "query": query,
        "summary": final_state.get("summary", ""),
        "issues": final_state.get("issues", []),
        "arguments": final_state.get("arguments", ""),
        "citation_verification": _serialize_citations(final_state.get("citation_verification")),
        "divergences": final_state.get("divergences", []),
        "outcome_prediction": final_state.get("outcome_prediction", {}),
        "judge_profiles": [p.__dict__ for p in final_state.get("judge_profiles", [])],
        "judge_analysis": final_state.get("judge_analysis", ""),
        "analytics": final_state.get("analytics", ""),
        "source_cases": [_serialize_case(c) for c in cases],
        "cases_analyzed": len(cases),
        "processing_time_seconds": elapsed,
        "prior_context": bool(prior_context),
    }


def _serialize_case(case) -> dict:
    return {
        "case_name": case.case_name,
        "court": case.court,
        "date_filed": case.date_filed,
        "url": case.absolute_url,
        "docket_number": case.docket_number,
        "excerpt": (case.snippet or "")[:400],
    }


def _serialize_citations(result) -> dict:
    if result is None:
        return {"total": 0, "valid": 0, "invalid": 0, "needs_review": 0, "citations": []}
    return {
        "total": result.total,
        "valid": result.valid,
        "invalid": result.invalid,
        "needs_review": result.needs_review,
        "citations": [c.__dict__ for c in result.citations],
    }
