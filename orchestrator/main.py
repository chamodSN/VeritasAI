from fastapi import FastAPI, Depends, HTTPException
import httpx
from pydantic import BaseModel
from common.security import verify_token
from common.logging import logger
from common.models import QueryRequest, QueryResponse, SearchRequest, SearchResponse, SummaryRequest, CitationRequest, PrecedentRequest, Case
from common.config import Config
from common.courtlistener_api import courtlistener_api
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Legal Case Orchestrator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def filter_supreme_court_cases(cases: list[dict]) -> list[dict]:
    return [case for case in cases if case.get("court_id") == "scotus" or case.get("court_citation_string", "").lower().startswith("united states supreme court")]


# Stub for MongoDB since no DB required
class MongoDB:
    @staticmethod
    async def get_query_result(user_id: str, query: str) -> dict:
        return None  # No cache

    @staticmethod
    async def cache_query_result(user_id: str, query: str, result: dict):
        pass  # No-op


@app.post("/query", response_model=QueryResponse)
async def process_query(request: QueryRequest, token: dict = Depends(verify_token)):
    try:
        user_id = token.get("sub")
        query = request.query
        logger.info(f"Processing query for user {user_id}: {query}")
        logger.debug(f"Received token claims: {token}")

        # Check cache (no-op)
        cached = await MongoDB.get_query_result(user_id, query)
        if cached:
            logger.info(f"Returning cached result for query: {query}")
            return QueryResponse(cases=cached["results"]["cases"])

        # Use the raw JWT token for downstream requests
        if 'token' not in token:
            logger.error("No raw_jwt in token claims")
            raise HTTPException(
                status_code=500, detail="Internal token processing error")
        auth_header = {"Authorization": f"Bearer {token['token']}"}

        # Step 1: Parse query via case_finder
        async with httpx.AsyncClient(timeout=30) as client:
            logger.debug(
                f"Sending request to case_finder: {Config.CASE_FINDER_URL}/parse_query with headers: {auth_header}")
            try:
                parse_res = await client.post(
                    f"{Config.CASE_FINDER_URL}/parse_query",
                    # Pass raw_query correctly
                    json=SearchRequest(raw_query=query).dict(),
                    headers=auth_header
                )
                parse_res.raise_for_status()
            except httpx.HTTPStatusError as e:
                logger.error(
                    f"Case Finder HTTP error: {e.response.status_code} - {e.response.text}", exc_info=True)
                raise HTTPException(
                    status_code=500, detail=f"Case Finder error: {e.response.status_code} - {e.response.text}")
            except httpx.RequestError as e:
                logger.error(
                    f"Case Finder connection error: {str(e)}", exc_info=True)
                raise HTTPException(
                    status_code=500, detail=f"Case Finder connection error: {str(e)}")
            search_req_data = parse_res.json()
            search_req = SearchRequest(**search_req_data)
            logger.debug(f"Parsed query: {search_req.dict()}")

            # Step 2: Search cases (Supreme Court filter optional)
            search_req_extended = {"num_results": 5, **search_req.dict()}
            logger.debug(f"Sending search request: {search_req_extended}")
            try:
                search_res = await client.post(
                    f"{Config.CASE_FINDER_URL}/search",
                    json=search_req_extended,
                    headers=auth_header
                )
                search_res.raise_for_status()
            except httpx.HTTPStatusError as e:
                logger.error(
                    f"Search HTTP error: {e.response.status_code} - {e.response.text}", exc_info=True)
                raise HTTPException(
                    status_code=500, detail=f"Search error: {e.response.status_code} - {e.response.text}")
            except httpx.RequestError as e:
                logger.error(
                    f"Search connection error: {str(e)}", exc_info=True)
                raise HTTPException(
                    status_code=500, detail=f"Search connection error: {str(e)}")
            search_response = SearchResponse(**search_res.json())
            logger.debug(f"Search response: {search_response.dict()}")

            # No forced Supreme Court filtering; keep results general across courts
            if not search_response.cases:
                logger.warning("No cases found")
                return QueryResponse(
                    cases=[],
                    case_type=search_req.case_type,
                    topic=search_req.topic,
                    date_from=search_req.date_from,
                    date_to=search_req.date_to
                )

            cases = []
            for case_data in search_response.cases:
                # Accept ids from raw CourtListener or curated Case objects
                case_id = str(
                    case_data.get("cluster_id")
                    or case_data.get("id")
                    or case_data.get("case_id")
                    or ""
                )
                if not case_id or case_id == "None":
                    logger.warning(f"Skipping invalid case_id: {case_id}")
                    continue

                case_name = case_data.get("caseName") or case_data.get("title") or "Unknown"
                court = case_data.get(
                    "court_citation_string", "United States Supreme Court")

                # Fetch full case text first; skip cases without enough text
                logger.debug(f"Fetching case text for case: {case_id}")
                try:
                    case_text = await courtlistener_api.get_case_text(case_id)
                except Exception as _e:
                    case_text = ""
                if not case_text or len(case_text) < 400:
                    logger.warning(f"Skipping case {case_id} due to insufficient text length: {len(case_text)}")
                    continue

                # Step 3: Summarize (use provided case_text)
                logger.debug(f"Summarizing case: {case_id}")
                summary = {"issue": "Summary error"}
                try:
                    summary_res = await client.post(
                        f"{Config.SUMMARY_URL}/summarize",
                        json=SummaryRequest(
                            case_id=case_id, case_data=case_data, case_text=case_text).dict(),
                        headers=auth_header
                    )
                    summary_res.raise_for_status()
                    summary = summary_res.json().get("summary", summary)
                except httpx.HTTPStatusError as e:
                    logger.error(
                        f"Summary HTTP error: {e.response.status_code} - {e.response.text}", exc_info=True)
                except Exception as e:
                    logger.error(
                        f"Summary error: {str(e)}", exc_info=True)
                # Ensure decision is available before any fallback construction
                decision = summary.get("decision", "Unknown")

                if summary.get("issue") == "Summary error":
                    # Build a graceful fallback summary from the case_text
                    import re
                    cleaned = re.sub(r"<.*?>", " ", case_text)
                    cleaned = re.sub(r"\s+", " ", cleaned).strip()
                    sentences = re.split(r'(?:\.|\?|!)\s+', cleaned)
                    fallback = " ".join(sentences[:5])
                    if len(fallback) > 800:
                        fallback = fallback[:780] + "..."
                    summary = {
                        "case": case_name,
                        "court": court,
                        "issue": fallback or "Summary unavailable.",
                        "decision": decision,
                        "entities": {"persons": [], "organizations": [], "locations": [], "legal_terms": []}
                    }

                # Refresh decision from possibly updated summary
                decision = summary.get("decision", "Unknown")

                # Step 4: Extract citations (use same case_text)
                logger.debug(f"Extracting citations for case: {case_id}")
                try:
                    citation_res = await client.post(
                        f"{Config.CITATION_URL}/extract_citations",
                        json=CitationRequest(case_id=case_id, case_text=case_text).dict(),
                        headers=auth_header
                    )
                    citation_res.raise_for_status()
                    citations = citation_res.json().get("citations", [])
                except httpx.HTTPStatusError as e:
                    logger.error(
                        f"Citation HTTP error: {e.response.status_code} - {e.response.text}", exc_info=True)
                except Exception as e:
                    logger.error(
                        f"Citation service error: {str(e)}", exc_info=True)
                    citations = []

                # Step 5: Find precedents
                logger.debug(f"Finding precedents for case: {case_id}")
                try:
                    precedent_res = await client.post(
                        f"{Config.PRECEDENT_URL}/find_precedents",
                        json=PrecedentRequest(case_id=case_id, citations=citations).dict(),
                        headers=auth_header
                    )
                    precedent_res.raise_for_status()
                    related_precedents_raw = precedent_res.json().get("related_cases", [])
                except httpx.HTTPStatusError as e:
                    logger.error(
                        f"Precedent HTTP error: {e.response.status_code} - {e.response.text}", exc_info=True)
                except Exception as e:
                    logger.error(
                        f"Precedent service error: {str(e)}", exc_info=True)
                    related_precedents_raw = []

                related_precedents = [
                    prec for prec in related_precedents_raw
                    if prec.get("date", "") <= "2025-12-31"
                ]

                cases.append(Case(
                    case_id=case_id,
                    title=case_name,
                    court=court,
                    decision=decision,
                    docket_id=case_data.get("docketNumber", None),
                    date=case_data.get("dateFiled", None),
                    summary=summary,
                    legal_citations=citations,
                    citations_count=len(citations),
                    related_precedents=related_precedents
                ))

            # Cache the results (no-op)
            await MongoDB.cache_query_result(user_id, query, {
                "results": {"cases": [case.dict() for case in cases]}
            })

            logger.info(f"Processed query successfully: {query}")
            return QueryResponse(
                cases=cases,
                case_type=search_req.case_type,
                topic=search_req.topic,
                date_from=search_req.date_from,
                date_to=search_req.date_to
            )
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error processing query: {str(e)}")
