import httpx
import asyncio
from typing import List, Dict, Any, Optional
from common.config import Config
from common.logging import logger


class CourtListenerAPI:
    def __init__(self):
        self.base_url = Config.COURTLISTENER_BASE_URL
        self.api_key = Config.COURTLISTENER_API_KEY
        self.headers = {
            "Authorization": f"Token {self.api_key}"} if self.api_key else {}
        logger.info(
            f"CourtListener API initialized with base_url: {self.base_url}")

    async def search_cases(
        self,
        query: str = "",
        court: str = "",
        case_type: str = "",
        topic: str = "",
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        page_size: int = 10
    ) -> Dict[str, Any]:
        if not self.api_key:
            raise ValueError("CourtListener API key is required")

        fielded_q = query.strip() or " "
        if court and court.strip():
            fielded_q += f" court_id:{court}"
        if date_from or date_to:
            date_range = f"{date_from or ''} TO {date_to or ''}"
            fielded_q += f" dateFiled:[{date_range}]"
        if case_type and case_type != "unknown":
            fielded_q += f" {case_type}"
        if topic and topic != "unknown":
            fielded_q += f" {topic}"

        params = {
            "q": fielded_q[:300],  # Reduced length for performance
            "type": "o",
            "page_size": min(page_size, 20),
            "fields": "id,cluster_id,caseName,court_citation_string,dateFiled,docketNumber,disposition,text,html_lawbox,html_columbia,html,html_with_citations"
        }

        async with httpx.AsyncClient(timeout=20) as client:
            try:
                response = await client.get(f"{self.base_url}search/", params=params, headers=self.headers)
                response.raise_for_status()
                data = response.json()
                return {
                    "results": data.get("results", []),
                    "count": data.get("count", len(data.get("results", []))),
                    "case_ids": [str(result.get("id", result.get("cluster_id", ""))) for result in data.get("results", [])]
                }
            except Exception as e:
                logger.error(f"Search error: {str(e)}")
                return {"results": [], "count": 0, "case_ids": []}

    async def get_case_details(self, case_id: str) -> Dict[str, Any]:
        if not self.api_key:
            raise ValueError("CourtListener API key is required")

        async with httpx.AsyncClient(timeout=20) as client:
            try:
                # Get cluster information with 'id' included
                cluster_response = await client.get(
                    f"{self.base_url}clusters/{case_id}/",
                    headers=self.headers,
                    params={
                        "fields": "id,case_name,case_name_short,court_name,docket_number,disposition"}
                )
                cluster_response.raise_for_status()
                cluster_data = cluster_response.json()

                # Get opinions for this case
                opinions_response = await client.get(
                    f"{self.base_url}opinions/",
                    params={
                        "cluster": case_id, "fields": "id,text,html_lawbox,html_columbia,html,html_with_citations,caseName,disposition,court_citation_string"},
                    headers=self.headers
                )
                opinions_response.raise_for_status()
                opinions_data = opinions_response.json()

                # Include the cluster_id at top level for easy access
                return {
                    "id": str(case_id),
                    "cluster": cluster_data,
                    "opinions": opinions_data.get("results", [])
                }
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error fetching case {case_id}: {str(e)}")
                return {}
            except Exception as e:
                logger.error(f"Error fetching case {case_id}: {str(e)}")
                return {}

    async def get_case_text(self, case_id: str) -> str:
        if not self.api_key:
            raise ValueError("CourtListener API key is required")

        async with httpx.AsyncClient(timeout=20) as client:
            try:
                response = await client.get(
                    f"{self.base_url}opinions/",
                    params={
                        "cluster": case_id, "fields": "id,text,html_lawbox,html_columbia,html,html_with_citations"},
                    headers=self.headers
                )
                response.raise_for_status()
                data = response.json()
                if data.get("results"):
                    opinion = data["results"][0]
                    text = (opinion.get("text") or
                            opinion.get("html_lawbox") or
                            opinion.get("html_columbia") or
                            opinion.get("html") or
                            opinion.get("html_with_citations") or "")
                    logger.info(
                        f"Extracted text for case {case_id}: {len(text)} characters")
                    return text
                return ""
            except httpx.HTTPStatusError as e:
                logger.error(
                    f"HTTP error fetching text for case {case_id}: {str(e)}")
                return ""
            except Exception as e:
                logger.error(
                    f"Error fetching text for case {case_id}: {str(e)}")
                return ""


courtlistener_api = CourtListenerAPI()
