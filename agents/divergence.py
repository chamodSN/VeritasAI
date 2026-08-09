# agents/divergence.py
"""
Jurisdiction Divergence Agent.
Detects when retrieved cases represent conflicting rulings across circuits/courts
on the same legal question. Pure analysis over already-retrieved cases — no
extra API call needed.
"""
from __future__ import annotations
import json
import re
from typing import Any

from agents.base_agent import BaseAgent
from core.logging import logger
from graph.state import AnalysisState


class DivergenceAgent(BaseAgent):

    @property
    def system_prompt(self) -> str:
        return (
            "You are a circuit split and jurisdiction divergence analyst. "
            "Given a set of cases from different courts, identify where courts disagree "
            "on the same legal question. For each divergence found:\n"
            "1. State the exact legal question in dispute\n"
            "2. List which courts/circuits rule which way, with the specific case name\n"
            "3. State whether SCOTUS has resolved it (and if so, how)\n"
            "4. Explain the practical implication for someone bringing this issue\n\n"
            "Return ONLY a JSON array. Each element:\n"
            "{\n"
            '  "question": "The exact legal question",\n'
            '  "split_type": "circuit_split" | "state_split" | "district_split",\n'
            '  "positions": [\n'
            '    {"court": "9th Circuit", "ruling": "...", "case": "Smith v. Jones"}\n'
            "  ],\n"
            '  "scotus_resolved": true | false,\n'
            '  "scotus_case": "case name or null",\n'
            '  "strategic_implication": "..."\n'
            "}\n"
            "If no divergence is found, return an empty array []."
        )

    def format_user_message(self, state: dict[str, Any]) -> str:
        query = state.get("query", "")
        cases = state.get("cases", [])
        summary = state.get("summary", "")

        case_list = "\n".join(
            f"- {c.case_name} | {c.court} | {c.date_filed} | Precedential: {c.precedential}"
            for c in cases
        )

        return (
            f"Query: {query}\n\n"
            f"Cases retrieved from multiple courts:\n{case_list}\n\n"
            f"Summary of holdings:\n{summary[:2000]}"
        )


def _parse_divergences(raw: str) -> list[dict]:
    try:
        cleaned = re.sub(r"```(?:json)?\s*|\s*```", "", raw).strip()
        match = re.search(r"\[[\s\S]*\]", cleaned)
        if match:
            return json.loads(match.group())
    except Exception:
        pass
    return []


async def divergence_node(state: AnalysisState) -> AnalysisState:
    """Only runs the LLM when cases come from 2+ different courts — otherwise a split is impossible."""
    cases = state.get("cases", [])
    courts = {getattr(c, "court", "") for c in cases}
    if len(courts) < 2:
        return {**state, "divergences": []}

    agent = DivergenceAgent()
    raw = await agent.run(state)
    divergences = _parse_divergences(raw)
    logger.info("divergences_found", count=len(divergences))
    return {**state, "divergences": divergences}