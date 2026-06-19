from abc import ABC, abstractmethod
from openai import AsyncOpenAI
from typing import Any


from core.config import settings

class BaseAgent(ABC):

    def __init__(self) -> None:
        self._llm = AsyncOpenAI (api_key=settings.OPENAI_API_KEY, 
         base_url=settings.API_BASE_URL)
        
    @property
    @abstractmethod
    def system_prompt(self) -> str:
        ...

    @abstractmethod
    def format_user_message(self, state: dict[str, Any]) -> str:
        ...

    