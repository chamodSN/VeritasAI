# orchestrator/main.py (Fixed spelling from orcherestrator. No other changes necessary as IR updates are in case_finder. RA handled in sub-agents.)
from fastapi import FastAPI, Depends, HTTPException
import httpx
from pydantic import BaseModel
from common.security import verify_token
from common.logging import logger
from common.models import QueryRequest, QueryResponse, SearchRequest, SearchResponse, SummaryRequest, CitationRequest, PrecedentRequest, Case
from common.config import Config
from common.db import MongoDB
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


@app.post("/query", response_model=QueryResponse)
async def process_query(request: QueryRequest, token: dict = Depends(verify_token)):
    try:
        user_id = token.get("sub")
        query = request.query
        logger.info(f"Processing query for user {user_id}: {query}")
        logger.debug(f"Received token claims: {token}")

        # Check cache
        cached = await MongoDB.get_query_result(user_id, query)
        if cached:
            logger.info(f"Returning cached result for query: {query}")
            return QueryResponse(cases=cached["results"]["cases"])

        # Use the raw JWT token for downstream requests
        if 'raw_jwt' not in token:
            logger.error("No raw_jwt in token claims")
            raise HTTPException(
                status_code=500, detail="Internal token processing error")
        auth_header = {"Authorization": f"Bearer {token['raw_jwt']}"}

        # Step 1: Parse query via case_finder
        async with httpx.AsyncClient(timeout=30) as client:
            logger.debug(
                f"Sending request to case_finder: {Config.CASE_FINDER_URL}/parse_query with headers: {auth_header}")
            try:
                parse_res = await client.post(
                    f"{Config.CASE_FINDER_URL}/parse_query",
                    json={"query": query},
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
            search_req_data['court'] = "scotus"
            search_req = SearchRequest(**search_req_data)
            logger.debug(f"Parsed query: {search_req.dict()}")

            # Step 2: Search cases with Supreme Court filter
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

            # Filter for Supreme Court cases
            search_response.cases = await filter_supreme_court_cases(search_response.cases)
            if not search_response.cases:
                logger.warning("No Supreme Court cases found")
                return QueryResponse(cases=[])

            cases = []
            for case_data in search_response.cases:
                case_id = str(case_data.get("cluster_id"))
                case_name = case_data.get("caseName", "Unknown")
                court = case_data.get(
                    "court_citation_string", "United States Supreme Court")

                # Step 3: Summarize
                logger.debug(f"Summarizing case: {case_id}")
                try:
                    summary_res = await client.post(
                        f"{Config.SUMMARY_URL}/summarize",
                        json=SummaryRequest(
                            case_id=case_id, case_data=case_data).dict(),
                        headers=auth_header
                    )
                    summary_res.raise_for_status()
                except httpx.HTTPStatusError as e:
                    logger.error(
                        f"Summary HTTP error: {e.response.status_code} - {e.response.text}", exc_info=True)
                    raise HTTPException(
                        status_code=500, detail=f"Summary error: {e.response.status_code} - {e.response.text}")
                summary = summary_res.json()["summary"]
                decision = summary.get("decision", "Unknown")

                # Step 4: Extract citations
                logger.debug(f"Extracting citations for case: {case_id}")
                try:
                    citation_res = await client.post(
                        f"{Config.CITATION_URL}/extract_citations",
                        json=CitationRequest(
                            case_id=case_id, case_data=case_data).dict(),
                        headers=auth_header
                    )
                    citation_res.raise_for_status()
                except httpx.HTTPStatusError as e:
                    logger.error(
                        f"Citation HTTP error: {e.response.status_code} - {e.response.text}", exc_info=True)
                    raise HTTPException(
                        status_code=500, detail=f"Citation error: {e.response.status_code} - {e.response.text}")
                citations = citation_res.json()["citations"]

                # Step 5: Find precedents
                logger.debug(f"Finding precedents for case: {case_id}")
                try:
                    precedent_res = await client.post(
                        f"{Config.PRECEDENT_URL}/find_precedents",
                        json=PrecedentRequest(
                            case_id=case_id, citations=citations).dict(),
                        headers=auth_header
                    )
                    precedent_res.raise_for_status()
                except httpx.HTTPStatusError as e:
                    logger.error(
                        f"Precedent HTTP error: {e.response.status_code} - {e.response.text}", exc_info=True)
                    raise HTTPException(
                        status_code=500, detail=f"Precedent error: {e.response.status_code} - {e.response.text}")
                related_precedents = [
                    prec for prec in precedent_res.json()["related_cases"]
                    if prec.get("date_filed", "") <= "2025-12-31"
                ]

                cases.append(Case(
                    case_id=case_id,
                    case_name=case_name,
                    court=court,
                    decision=decision,
                    summary=summary,
                    citations=citations,
                    related_precedents=related_precedents
                ))

            response = QueryResponse(cases=cases)
            await MongoDB.store_query_result(user_id, query, response.dict())
            logger.info(
                f"Query processed successfully: {len(cases)} cases returned")
            return response

    except httpx.HTTPStatusError as e:
        logger.error(
            f"HTTP error during query processing: {str(e)}", exc_info=True)
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error processing query: {str(e)}")
