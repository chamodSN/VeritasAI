""""Main orchestrator service for handling legal case queries.
It exposes a /query endpoint, which coordinates communication between three agents:"""
import os
import asyncio

import httpx
from fastapi import FastAPI, Request
from pydantic import BaseModel

from common.http import sign_request, error_response

app = FastAPI()

CASE_FINDER_URL = os.getenv("CASE_FINDER_URL")
SUMMARY_URL = os.getenv("SUMMARY_URL")
CITATION_URL = os.getenv("CITATION_URL")


class QueryRequest(BaseModel):
    """Define the Request Model"""
    query: str
    jurisdiction: str | None = None
    date_range: tuple[str, str] | None = None
    top_k: int | None = 5


@app.post("/query")
async def query_case(req: QueryRequest, request: Request):
    """Handles the /query endpoint for processing legal case queries."""
    async with httpx.AsyncClient() as client:
        # Step 1: Case Finder
        headers = sign_request("POST", "/search", req.dict())
        r = await client.post(CASE_FINDER_URL, json=req.dict(), headers=headers)
        if r.status_code != 200:
            return error_response("CASE_FINDER_FAIL", "Case Finder error")
        cases = r.json().get("results", [])

        # Step 2: Summarize each case
        async def summarize_case(c):
            h = sign_request("POST", "/summarize", c)
            r2 = await client.post(SUMMARY_URL, json=c, headers=h)
            return r2.json()

        summaries = await asyncio.gather(*[summarize_case(c) for c in cases[:req.top_k]])

        # Step 3: Format citations
        async def format_citation(c):
            h = sign_request("POST", "/format", c)
            r3 = await client.post(CITATION_URL, json=c, headers=h)
            return r3.json()

        citations = await asyncio.gather(*[format_citation(c) for c in cases[:req.top_k]])

    return {"query": req.query, "cases": cases, "summaries": summaries, "citations": citations}
