# agents/outcome_predictor.py
"""
Outcome Prediction Agent.
Produces a transparent, case-grounded outcome signal — every supporting/opposing
case is named, every factor is explained. Not a black-box model: a heuristic
read of the actual retrieved cases, honest about uncertainty.
"""
from __future__ import annotations
import json
import re
from typing import Any
from agents.base_agent import BaseAgent
from graph.state import AnalysisState


class OutcomePredictorAgent(BaseAgent):

    @property
    def system_prompt(self) -> str:
        return (
            "You are a legal outcome analyst. Based on the retrieved case data, "
            "produce an outcome prediction for the user's legal question.\n\n"
            "Important rules:\n"
            "- Only use data from the provided cases — do not invent statistics\n"
            "- Be transparent: show which cases support each outcome estimate\n"
            "- Never express false precision — use ranges, not single percentages\n"
            "- Always include a confidence level and its basis\n\n"
            "Return ONLY this JSON structure:\n"
            "{\n"
            '  "favorable_outcome_likelihood": "high|medium|low|insufficient_data",\n'
            '  "confidence": "high|medium|low",\n'
            '  "confidence_basis": "explanation of confidence level",\n'
            '  "supporting_cases": ["case names where outcome favoured similar position"],\n'
            '  "opposing_cases": ["case names where outcome went the other way"],\n'
            '  "key_factors": ["factor 1", "factor 2"],\n'
            '  "risk_factors": ["risk 1", "risk 2"],\n'
            '  "recommended_approach": "brief strategic recommendation",\n'
            '  "disclaimer": "This is a research tool, not legal advice. '
            'Outcomes depend on facts and jurisdiction not captured here."\n'
            "}"
        )

    def format_user_message(self, state: dict[str, Any]) -> str:
        query = state.get("query", "")
        cases = state.get("cases", [])
        issues = state.get("issues", [])

        case_data = []
        for c in cases:
            case_data.append(
                f"Case: {c.case_name}\n"
                f"  Court: {c.court} | Date: {c.date_filed}\n"
                f"  Precedential: {c.precedential} | Citations: {c.citation_count or 0}\n"
                f"  Excerpt: {(c.snippet or '')[:400]}"
            )

        return (
            f"Legal question: {query}\n\n"
            f"Issues identified: {'; '.join(issues[:5])}\n\n"
            f"Cases retrieved:\n\n"
            + "\n\n".join(case_data[:8])
        )


def _parse_prediction(raw: str) -> dict:
    try:
        cleaned = re.sub(r"```(?:json)?\s*|\s*```", "", raw).strip()
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if match:
            return json.loads(match.group())
    except Exception:
        pass
    return {"favorable_outcome_likelihood": "insufficient_data", "confidence": "low"}


async def outcome_predictor_node(state: AnalysisState) -> AnalysisState:
    agent = OutcomePredictorAgent()
    raw = await agent.run(state)
    prediction = _parse_prediction(raw)
    return {**state, "outcome_prediction": prediction}