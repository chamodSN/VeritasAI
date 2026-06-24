from __future__ import annotations
from typing import Any
from agents.base_agent import BaseAgent
from graph.state import AnalysisState


class ArgumentAgent(BaseAgent):

    @property
    def system_prompt(self) -> str:
        return (
            "You are a senior litigator. Based on the identified legal issues and case law provided, "
            "construct well-reasoned legal arguments. For each major issue:\n"
            "1. State the argument clearly\n"
            "2. Support it with specific case holdings from the provided cases\n"
            "3. Address the strongest counterargument\n"
            "4. Explain precedential strength\n\n"
            "Only cite cases that were provided to you. Do not invent citations."
        )

    def format_user_message(self, state: dict[str, Any]) -> str:
        query = state.get("query", "")
        issues = state.get("issues", [])
        cases = state.get("cases", [])

        issues_text = "\n".join(f"- {issue}" for issue in issues)
        case_refs = "\n".join(
            f"- {c.case_name} ({c.court}, {c.date_filed}): "
            f"{(c.full_text or c.snippet or 'N/A')[:500]}"
            for c in cases[:8]
        )

        return (
            f"Research query: {query}\n\n"
            f"Identified legal issues:\n{issues_text}\n\n"
            f"Relevant cases:\n{case_refs}"
        )


async def argument_node(state: AnalysisState) -> AnalysisState:
    agent = ArgumentAgent()
    arguments = await agent.run(state)
    return {**state, "arguments": arguments}