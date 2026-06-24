# agents/issue_extractor.py
from __future__ import annotations
import json
import re
from typing import Any
from agents.base_agent import BaseAgent
from graph.state import AnalysisState
from core.logging import logger


class IssueExtractorAgent(BaseAgent):

    @property
    def system_prompt(self) -> str:
        return (
            "You are a legal issue identification specialist. "
            "Extract and categorize the primary and secondary legal issues from the provided text. "
            "Return a JSON array of strings. Each string is one clearly stated legal issue. "
            "Maximum 10 issues. Return ONLY the JSON array, no other text."
        )

    def format_user_message(self, state: dict[str, Any]) -> str:
        query = state.get("query", "")
        summary = state.get("summary", "")
        return f"Legal query: {query}\n\nCase summary:\n{summary[:3000]}"


def _parse_issues(raw: str) -> list[str]:
    """Parse JSON array from LLM output, with fallback to line-splitting."""
    try:
        cleaned = re.sub(r"```(?:json)?\s*|\s*```", "", raw).strip()
        issues = json.loads(cleaned)
        if isinstance(issues, list):
            return [str(i).strip() for i in issues if i]
    except (json.JSONDecodeError, ValueError):
        logger.warning("issue_parse_fallback")
        lines = [line.strip().lstrip("0123456789.-) ") for line in raw.splitlines()]
        return [l for l in lines if len(l) > 10][:10]
    return []


async def issue_extractor_node(state: AnalysisState) -> AnalysisState:
    agent = IssueExtractorAgent()
    raw = await agent.run(state)
    issues = _parse_issues(raw)
    return {**state, "issues": issues}