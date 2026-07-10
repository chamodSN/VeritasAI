# agents/analytics.py
from __future__ import annotations
from typing import Any
from agents.base_agent import BaseAgent
from graph.state import AnalysisState


class AnalyticsAgent(BaseAgent):
    @property
    def system_prompt(self) -> str:
        return (
            "You are a legal analytics specialist. Identify:\n"
            "1. Jurisdictional patterns\n2. Temporal trends\n"
            "3. Precedential strength\n4. Cross-cutting themes\n5. Strategic insights\n"
            "Reference specific cases by name."
        )

    def format_user_message(self, state: dict[str, Any]) -> str:
        cases = state.get("cases", [])
        case_list = "\n".join(f"- {c.case_name} | {c.court} | {c.date_filed} | "
                              f"Precedential: {c.precedential} | Citations: {c.citation_count or 0}"
                              for c in cases)
        return (f"Query: {state.get('query', '')}\n\n"
                f"Issues: {', '.join(state.get('issues', []))}\n\n"
                f"Cases ({len(cases)} total):\n{case_list}")


async def analytics_node(state: AnalysisState) -> AnalysisState:
    return {**state, "analytics": await AnalyticsAgent().run(state)}