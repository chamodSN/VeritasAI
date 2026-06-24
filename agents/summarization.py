# agents/summarization.py
from __future__ import annotations
from typing import Any
from agents.base_agent import BaseAgent
from graph.state import AnalysisState


class SummarizationAgent(BaseAgent):

    @property
    def system_prompt(self) -> str:
        return (
            "You are a senior legal analyst. Synthesize the provided case excerpts into a "
            "comprehensive summary covering: key legal principles, main holdings, and strategic "
            "significance. Be concise but complete. Use plain English suitable for a lawyer "
            "reviewing the research. Do not fabricate case details not present in the input."
        )

    def format_user_message(self, state: dict[str, Any]) -> str:
        query = state.get("query", "")
        cases = state.get("cases", [])

        case_texts = []
        for i, case in enumerate(cases[:10], 1):
            text = case.full_text or case.snippet or "No text available"
            case_texts.append(
                f"Case {i}: {case.case_name} ({case.court}, {case.date_filed})\n{text[:1500]}"
            )

        return (
            f"Research query: {query}\n\n"
            f"Relevant cases retrieved:\n\n"
            + "\n\n---\n\n".join(case_texts)
        )


async def summarization_node(state: AnalysisState) -> AnalysisState:
    agent = SummarizationAgent()
    summary = await agent.run(state)
    return {**state, "summary": summary}