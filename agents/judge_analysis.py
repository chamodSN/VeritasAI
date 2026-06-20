from __future__ import annotations
from typing import Any
from agents.base_agent import BaseAgent
from graph.state import AnalysisState


class JudgeAnalysisAgent(BaseAgent):

    @property
    def system_prompt(self) -> str:
        return (
            "You are a litigation strategist specialising in judicial analytics. "
            "Given a judge's profile (appointing president, law school, practice area history, "
            "political affiliation, recent opinions), provide specific strategic guidance:\n"
            "1. Likely judicial philosophy and how it affects this case type\n"
            "2. Argument framing that resonates with this judge's background\n"
            "3. Procedural tendencies to expect (strict deadlines, oral argument style)\n"
            "4. Red flags or opportunities based on similar prior rulings\n\n"
            "Be specific. Reference the judge by name. Do NOT generalise."
        )

    def format_user_message(self, state: dict[str, Any]) -> str:
        query = state.get("query", "")
        profiles = state.get("judge_profiles", [])
        if not profiles:
            return f"No specific judge identified for query: {query}"

        profile_texts = []
        for p in profiles:
            profile_texts.append(
                f"Judge: {p.name}\n"
                f"Court: {p.court}\n"
                f"Appointed by: {p.appointing_president or 'Unknown'}\n"
                f"Political affiliation: {p.political_affiliation or 'Unknown'}\n"
                f"Law school: {p.law_school or 'Unknown'}\n"
                f"Total opinions authored: {p.total_opinions}\n"
                f"Primary practice areas: {', '.join(p.practice_areas)}\n"
                f"Recent cases: {', '.join(op['case_name'] for op in p.recent_opinions[:5])}"
            )

        return (
            f"Research query: {query}\n\n"
            f"Judge profiles found:\n\n"
            + "\n\n---\n\n".join(profile_texts)
        )


async def judge_analysis_node(state: AnalysisState) -> AnalysisState:
    if not state.get("judge_profiles"):
        return {**state, "judge_analysis": ""}
    agent = JudgeAnalysisAgent()
    result = await agent.run(state)
    return {**state, "judge_analysis": result}