from __future__ import annotations

import httpx
import asyncio
import urllib.parse

from dataclasses import dataclass, field
from typing import Optional, Any
from openai import AsyncOpenAI

from core.config import settings
from core.exceptions import ExternalServiceError
from core.logging import logger

@dataclass
class CaseResult:
    case_name: str
    court: str
    date_filed: str
    absolute_url: str
    cluster_id: str
    docket_number: Optional[str] = None
    citation_count: Optional[int] = None
    precedential: bool = True
    nature_of_suit: Optional[str] = None
    judge: Optional[str] = None
    court_id: Optional[str] = None
    snippet: Optional[str] = None
    opinion_ids: list[int] = field(default_factory=list)
    full_text: Optional[str] = None
    casebody_text: Optional[str] = None

@dataclass
class AlertResult:
    id: int
    name:str
    query:str
    rate:str
    alert_type: str
    resource_uri: str
    date_created: str
    date_last_hit: Optional[str] = None

class CourtListenerClient:
    BASE_URL = "https://www.courtlistener.com/api/rest/v4"
    MAX_RETRIES = 3 # how many times to retry on rate-limit errors
    BACKOFF_BASE = 2.0 # base number (seconds) used to calculate wait time between retries

    def __init__(self) ->None:
        self._headers = {
            "Authorization": f"Token {settings.COURTLISTENER_API_KEY}",
            "Accept": "application/json"
        }
        self._http: httpx.AsyncClient | None = None
        self._llm = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY, 
            base_url=settings.API_BASE_URL
    )
        
    async def __aenter__(self) -> "CourtListenerClient":
        self._http = httpx.AsyncClient(follow_redirects=True, headers=self._headers, timeout=30.0)
        return self

    async def __aexit__(self, *_:Any) -> None:
        if self._http:
            await self._http.aclose()

    def _client(self) -> httpx.AsyncClient:
        if self._http:
            return self._http
        return httpx.AsyncClient(follow_redirects=True, headers=self._headers, timeout=30.0)
        
    async def _get_with_retry(self, url:str,params:dict|None=None) -> dict:
        client = self._client()
        try:
            for attempt in range(self.MAX_RETRIES):
                response = await client.get(url, params=params)
                if response.status_code == 429:  # Rate limit error
                    wait_time = self.BACKOFF_BASE ** attempt
                    await asyncio.sleep(wait_time)
                    continue

                response.raise_for_status()
                return response.json()
            
            raise ExternalServiceError("CourtListener rate limit exceeded after retries")

        except httpx.HTTPStatusError as exc:
            logger.error("courtlistener_http_error", status=exc.response.status_code, url=url)
            raise ExternalServiceError(f"CourtListener returned {exc.response.status_code}")
        except httpx.RequestError as exc:
            logger.error("courtlistener_network_error", error=str(exc))
            raise ExternalServiceError("CourtListener is unreachable")
        finally:
            if not self._http:
                await client.aclose()

    # Search CourtListener opinions.
    async def search_cases(self, query: str, max_results: int = 10) -> list[CaseResult]:
        expanded = await self.expand_query(query)

        page_size = min(max_results, 20)  # CourtListener max page_size for search

        params = {
            "q": expanded,
            "type": "o",           # opinion clusters - published-only by default
            "order_by": "score desc",
            "page_size": page_size,
        }

        data = await self._get_with_retry(f"{self.BASE_URL}/search/", params=params)

        results: list[CaseResult] = []
        for item in data.get("results", [])[:max_results]:
            opinions_nested = item.get("opinions", [])
            opinion_ids = [op["id"] for op in opinions_nested if "id" in op]
            snippet = opinions_nested[0].get("snippet", "") if opinions_nested else ""

            results.append(CaseResult(
                case_name=item.get("caseName", "Unknown"),
                court=item.get("court", "Unknown"),
                date_filed=item.get("dateFiled", ""),
                absolute_url=f"https://www.courtlistener.com{item.get('absolute_url', '')}",
                cluster_id=str(item.get("cluster_id", "")),
                docket_number=item.get("docketNumber"),
                citation_count=item.get("citeCount"),
                precedential=item.get("status", "") == "Published",
                nature_of_suit=item.get("suitNature"),
                judge=item.get("judge"),
                court_id=item.get("court_id"),
                snippet=snippet,
                opinion_ids=opinion_ids,
            ))

        logger.info("cases_found", count=len(results), query=query[:60])
        return results

    #Fetch full opinion text, preferring html_with_citations per docs.
    async def fetch_opinion_text(self, opinion_id: int) -> str:
        params = {"fields": "id,html_with_citations,plain_text"}
        data = await self._get_with_retry(
            f"{self.BASE_URL}/opinions/{opinion_id}/",
            params=params,
        )

        for field_name in ("html_with_citations", "plain_text"):
            text = data.get(field_name, "") or ""
            if text.strip():
                return text[:5000]  # Cap per case

        return ""

    #Fetch full opinion text for the top N cases.
    async def enrich_cases_with_text(self, cases: list[CaseResult]) -> list[CaseResult]:
        enriched = []
        for i, case in enumerate(cases):
            if i >= 5:
                enriched.append(case)
                continue

            if case.opinion_ids:
                try:
                    text = await self.fetch_opinion_text(case.opinion_ids[0])
                    case.full_text = text
                except ExternalServiceError:
                    case.full_text = case.snippet
            else:
                case.full_text = case.snippet

            enriched.append(case)

            if i < len(cases) - 1 and i < 4:
                await asyncio.sleep(0.5)

        return enriched

    # Verify a citation exists using CourtListener's Citation Lookup API.
    async def lookup_citation(self, citation: str) -> dict | None:
        """
        Returns the matching cluster data if found, None if the citation
        doesn't exist.
        """
        try:
            data = await self._get_with_retry(
                f"{self.BASE_URL}/citation-lookup/",
                params={"citation": citation},
            )
            results = data.get("results", [])
            return results[0] if results else None
        except ExternalServiceError:
            return None

    # Create a CourtListener search alert.
    async def create_alert(self, query: str, name: str, rate: str = "dly") -> Optional[str]:

        query_string = f"q={urllib.parse.quote(query)}&type=o"

        valid_rates = {"rt", "dly", "wly", "mly"}
        if rate not in valid_rates:
            rate = "dly"

        client = self._client()
        try:
            resp = await client.post(
                f"{self.BASE_URL}/alerts/",
                data={
                    "name": name,
                    "query": query_string,
                    "rate": rate,
                    "alert_type": "o",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            logger.info("alert_created", name=name, id=data.get("id"))
            return data.get("resource_uri")
        except Exception as exc:
            logger.error("alert_create_failed", error=str(exc))
            return None
        finally:
            if not self._http:
                await client.aclose()

    # List all search alerts for the authenticated user.
    async def get_alerts(self) -> list[AlertResult]:
        try:
            data = await self._get_with_retry(f"{self.BASE_URL}/alerts/")
            return [
                AlertResult(
                    id=item["id"],
                    name=item.get("name", ""),
                    query=item.get("query", ""),
                    rate=item.get("rate", ""),
                    alert_type=item.get("alert_type", "o"),
                    resource_uri=item.get("resource_uri", ""),
                    date_created=item.get("date_created", ""),
                    date_last_hit=item.get("date_last_hit"),
                )
                for item in data.get("results", [])
            ]
        except ExternalServiceError:
            return []

    # Delete a search alert by its integer ID.
    async def delete_alert(self, alert_id: int) -> bool:
        client = self._client()
        try:
            resp = await client.delete(f"{self.BASE_URL}/alerts/{alert_id}/")
            return resp.status_code in (200, 204)
        except Exception as exc:
            logger.error("alert_delete_failed", id=alert_id, error=str(exc))
            return False
        finally:
            if not self._http:
                await client.aclose()

courtlistener_client = CourtListenerClient()
