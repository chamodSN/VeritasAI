"""query the CourtListener API."""
import os
import httpx
from dotenv import load_dotenv
from .models import CaseDoc

# Load env variables
load_dotenv()
COURTLISTENER_URL = os.getenv("COURTLISTENER_URL")


async def search_cases(query: str, top_k: int = 5) -> list[CaseDoc]:
    if not COURTLISTENER_URL:
        raise ValueError(
            "COURTLISTENER_URL is not set in environment variables!")

    async with httpx.AsyncClient() as client:
        resp = await client.get(COURTLISTENER_URL, params={"search": query, "page_size": top_k})
        resp.raise_for_status()
        data = resp.json()

        results = []
        for d in data.get("results", []):
            results.append(CaseDoc(
                id=str(d["id"]),
                title=d.get("absolute_url", "Unknown").split(
                    "/")[-1].replace("-", " ").title(),
                court="Unknown",  # No court info in v4 JSON; can enrich later
                date=d.get("date_created", ""),
                # list of URLs for cited opinions
                citation=", ".join(d.get("opinions_cited", [])),
                url="https://www.courtlistener.com" +
                    d.get("absolute_url", ""),
                full_text=d.get("html_with_citations") or d.get(
                    "plain_text", None),
            ))

        return results
