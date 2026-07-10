# agents/base_agent.py
from __future__ import annotations
import asyncio
from abc import ABC, abstractmethod
from typing import Any
from openai import AsyncOpenAI
from core.config import settings
from core.logging import logger


class BaseAgent(ABC):
    def __init__(self) -> None:
        self._llm = AsyncOpenAI(api_key=settings.OPENAI_API_KEY, base_url=settings.API_BASE_URL)

    @property
    @abstractmethod
    def system_prompt(self) -> str: ...

    @abstractmethod
    def format_user_message(self, state: dict[str, Any]) -> str: ...

    async def run(self, state: dict[str, Any]) -> str:
        agent_name = self.__class__.__name__
        try:

            response = await self._llm.chat.completions.create(
                model=settings.LLM_MODEL, 
                temperature=settings.TEMPERATURE, 
                max_tokens=2000,
                messages=[{"role": "system", "content": self.system_prompt},
                          {"role": "user", "content": self.format_user_message(state)}],
            )
            result = response.choices[0].message.content or ""

            if response.usage and state.get("user_id"):

                from services.usage import usage_tracker

                asyncio.create_task(usage_tracker.record(
                    user_id=state["user_id"], request_id=state.get("request_id", "unknown"),
                    agent_name=agent_name, model=settings.LLM_MODEL,
                    input_tokens=response.usage.prompt_tokens,
                    output_tokens=response.usage.completion_tokens,
                ))

            logger.info(f"{agent_name}_completed")

            return result
        
        except Exception as exc:
            logger.error(f"{agent_name}_failed", error=str(exc))
            return ""