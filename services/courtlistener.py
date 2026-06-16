from __future__ import annotations

import asyncio
import httpx

from dataclasses import dataclass
from typing import Optional, Any
from VeritasAI.core.config import settings
from openai import AsyncOpenAI

@dataclass
class caseResult:
    case_name: str
    court: str
    date_filed: str
    absolute_url: str
    resource_url: str
    cluster_id: str
    docket_number: Optional[str] = None
    citation_count: Optional[int] = None
    precedential: Optional[bool] = None
    nature_of_suit: Optional[str] = None
    casebody_text: Optional[str] = None

@dataclass
class AlertResult:
    name:str
    query:str
    rate:str
    resource_uri:str
    date_created:str
    is_active:bool

class CourtListenerClient:
    BASE_URL = "https://www.courtlistener.com/api/rest/v4"

    def __init__(self) ->None:
        self._headers = {
            "Authorization": f"Token {settings.COURTLISTENER_API_KEY}",
            "Content-Type": "application/json"
        }
        self._http: httpx.AsyncClient | None = None
        self._llm = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY, 
            base_url=settings.API_BASE_URL
    )
        
    async def __aenter__(self) -> "CourtListenerClient":
        self._http = httpx.AsyncClient(headers=self._headers, timeout=30.0)
        return self

    async def __aexit__(self, *_:Any) -> None:
        if self._http:
            await self._http.aclose()

    def _client(self) -> httpx.AsyncClient:
        if self._http:
            return self._http
        return httpx.AsyncClient(headers=self._headers, timeout=30.0)
        
