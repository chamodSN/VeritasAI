import httpx
import asyncio
from typing import List, Dict, Any, Optional
from common.config import Config
from common.logging import logger
from bs4 import BeautifulSoup
import re
from sentence_transformers import SentenceTransformer
from sentence_transformers.util import cos_sim
import numpy as np

embed_model = SentenceTransformer('all-MiniLM-L6-v2')


class CourtListenerAPI:
    def __init__(self):
        self.base_url = Config.COURTLISTENER_BASE_URL
        self.api_key = Config.COURTLISTENER_API_KEY
        self.headers_cl = {
            "Authorization": f"Token {self.api_key}"} if self.api_key else {}

    def _sanitize_query(self, query: str) -> str:
        query = query.strip()
        return query[:300]

    async def search_cases(self, query: str = "", court: str = "", date_from: Optional[str] = None, date_to: Optional[str] = None, page_size: int = 10) -> Dict[str, Any]:
        sanitized_q = self._sanitize_query(query)
        if court.strip():
            sanitized_q += f" court_id:{court}"

        if date_from or date_to:
            from_str = date_from or '*'
            to_str = date_to or '*'
            sanitized_q += f" date_filed:[{from_str} TO {to_str}]"

        params = {
            "q": sanitized_q,
            "type": "o",
            "fields": "id,cluster_id,case_name,court,date_filed,plain_text,html_with_citations,snippet,disposition,docket_number"
        }

        async with httpx.AsyncClient(timeout=20) as client:
            try:
                res = await client.get(f"{self.base_url}search/", params=params, headers=self.headers_cl)
                res.raise_for_status()
                data = res.json()
                results = data.get("results", [])
                return {"results": results, "count": data.get("count", len(results))}
            except Exception as e:
                logger.error(f"CourtListener search error: {str(e)}")
                return {"results": [], "count": 0}

    def _clean_text(self, c: Dict) -> str:
        text = c.get('html_with_citations', '') or c.get(
            'plain_text', '') or c.get('snippet', '')[:500]
        if '<' in text:
            soup = BeautifulSoup(text, 'html.parser')
            text = soup.get_text()
        return re.sub(r'\s+', ' ', text).strip()

    async def get_case_details(self, case_id: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=20) as client:
            try:
                cluster_res = await client.get(f"{self.base_url}clusters/{case_id}/", headers=self.headers_cl, params={"fields": "id,case_name,court,date_filed,disposition,docket_number"})
                cluster_res.raise_for_status()
                cluster_data = cluster_res.json()

                opinions_res = await client.get(f"{self.base_url}opinions/", params={"cluster": case_id, "fields": "id,plain_text,html_with_citations"}, headers=self.headers_cl)
                opinions_res.raise_for_status()
                opinions_data = opinions_res.json().get("results", [])

                return {"cluster": cluster_data, "opinions": opinions_data}
            except Exception as e:
                logger.error(f"Error fetching details: {str(e)}")
                return {}

    async def get_case_text(self, case_id: str) -> str:
        async with httpx.AsyncClient(timeout=25) as client:
            try:
                res = await client.get(f"{self.base_url}opinions/", params={"cluster": case_id, "fields": "plain_text,html_with_citations"}, headers=self.headers_cl)
                res.raise_for_status()
                data = res.json()
                if data.get("results"):
                    opinion = data["results"][0]
                    text = opinion.get("html_with_citations",
                                       "") or opinion.get("plain_text", "")
                    if '<' in text:
                        soup = BeautifulSoup(text, 'html.parser')
                        text = soup.get_text()
                    return re.sub(r'\s+', ' ', text).strip()
                return ""
            except Exception as e:
                logger.error(f"Error fetching text: {str(e)}")
                return ""


courtlistener_api = CourtListenerAPI()
