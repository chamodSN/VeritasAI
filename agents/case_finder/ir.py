"""query the CourtListener API."""
import os
import httpx
from .models import CaseDoc

COURTLISTENER_URL = os.getenv("COURTLISTENER_URL")


async def search_cases(query: str, top_k: int = 5) -> list[CaseDoc]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(COURTLISTENER_URL, params={"search": query, "page_size": top_k})
        # https://www.courtlistener.com/api/rest/v3/opinions/?search=climate+change&page_size=5
        data = resp.json()
        results = []
        for d in data.get("results", []):
            results.append(CaseDoc(
                id=str(d["id"]),
                title=d.get("caseName", "Unknown"),
                court=d.get("court", {}).get("name", "Unknown"),
                date=d.get("dateFiled", ""),
                citation=d.get("citation", None),
                url=d.get("absolute_url", None),
                full_text=d.get("plain_text", None),
            ))
        return results
