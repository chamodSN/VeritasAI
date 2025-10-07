from fastapi import FastAPI, Depends, HTTPException
import httpx
from pydantic import BaseModel
from common.security import verify_token
from common.logging import logger
from common.models import QueryRequest, QueryResponse, SearchRequest, SearchResponse, SummaryRequest, CitationRequest, PrecedentRequest, Case
from common.config import Config
from common.courtlistener_api import courtlistener_api
from fastapi.middleware.cors import CORSMiddleware
import re

app = FastAPI(title="Legal Case Orchestrator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Broadened for testing; restrict in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/query", response_model=QueryResponse)
async def process_query(request: QueryRequest, token: dict = Depends(verify_token)):
    try:
        user_id = token.get("sub")
        query = request.query
        logger.info(f"Processing query for user {user_id}: {query}")

        auth_header = {"Authorization": f"Bearer {token['token']}"}

        async with httpx.AsyncClient(timeout=30) as client:
            # Step 1: Parse query
            try:
                parse_res = await client.post(
                    f"{Config.CASE_FINDER_URL}/parse_query",
                    json=SearchRequest(raw_query=query).dict(),
                    headers=auth_header
                )
                parse_res.raise_for_status()
                search_req_data = parse_res.json()
                search_req = SearchRequest(**search_req_data)
                logger.info(
                    f"Parsed query: case_type={search_req.case_type}, topic={search_req.topic}, raw_query={search_req.raw_query[:100]}...")
            except Exception as parse_err:
                logger.error(f"Parse query failed: {str(parse_err)}")
                raise HTTPException(
                    status_code=500, detail="Query parsing failed")

            # Step 2: Search cases (with fallbacks)
            search_response = None
            search_req_simple = SearchRequest(
                raw_query=query, **{k: v for k, v in search_req.dict().items() if k != 'raw_query'})
            for attempt in range(3):
                try:
                    if attempt == 0:
                        # Try expanded query with dates
                        payload = {
                            "num_results": request.per_page, **search_req.dict()}
                        logger.info(
                            f"Search attempt {attempt + 1}: Using expanded query with dates")
                    elif attempt == 1:
                        # Fallback to simple original query with dates
                        payload = {
                            "num_results": request.per_page, **search_req_simple.dict()}
                        logger.info(
                            f"Search attempt {attempt + 1}: Falling back to simple query with dates '{query}'")
                    else:
                        # Fallback to simple query without dates
                        payload = {
                            "num_results": request.per_page, **search_req_simple.dict()}
                        payload['date_from'] = None
                        payload['date_to'] = None
                        logger.info(
                            f"Search attempt {attempt + 1}: Simple query without date filter")

                    search_res = await client.post(
                        f"{Config.CASE_FINDER_URL}/search",
                        json=payload,
                        headers=auth_header
                    )
                    search_res.raise_for_status()
                    search_response = SearchResponse(**search_res.json())
                    logger.info(
                        f"Found {len(search_response.cases)} cases on attempt {attempt + 1}")

                    if len(search_response.cases) > 0:
                        break  # Success, proceed

                except Exception as search_err:
                    logger.error(
                        f"Search attempt {attempt + 1} failed: {str(search_err)}")
                    continue

            if not search_response or not search_response.cases:
                logger.warning("No cases found after all search attempts")
                return QueryResponse(
                    cases=[],
                    case_type=search_req.case_type,
                    topic=search_req.topic,
                    date_from=search_req.date_from,
                    date_to=search_req.date_to
                )

            cases = []
            max_cases = min(request.per_page, len(search_response.cases))
            for case_data in search_response.cases[:max_cases]:
                case_id = str(case_data.get("case_id") or "")
                if not case_id:
                    logger.warning("Skipping case with missing ID")
                    continue

                case_name = case_data.get("title") or "Unknown"
                court = case_data.get("court", "Unknown Court")
                logger.info(f"Processing case {case_id}: {case_name}")

                # Fetch full case text
                try:
                    case_text = await courtlistener_api.get_case_text(case_id)
                    if not case_text or len(case_text) < 400:
                        logger.warning(f"Insufficient text for case {case_id}")
                        continue
                except Exception as text_err:
                    logger.error(
                        f"Failed to fetch text for {case_id}: {str(text_err)}")
                    continue

                # Step 3: Summarize
                summary = {"case": case_name, "court": court,
                           "issue": "Summary unavailable", "decision": "Unknown", "entities": {}}
                try:
                    async with httpx.AsyncClient(timeout=10.0) as summ_client:
                        summary_res = await summ_client.post(
                            f"{Config.SUMMARY_URL}/summarize",
                            json=SummaryRequest(
                                case_id=case_id, case_data=case_data, case_text=case_text).dict(),
                            headers=auth_header
                        )
                        summary_res.raise_for_status()
                        summary_data = summary_res.json()
                        summary = summary_data.get("summary", summary)
                    logger.info(f"Summarized case {case_id}")
                except Exception as summ_err:
                    logger.error(
                        f"Summary failed for {case_id}: {str(summ_err)}")
                    sentences = re.split(r'(?:\.|\?|!)\s+', case_text)
                    fallback = " ".join(sentences[:5])[:780] + "..."
                    summary = {"case": case_name, "court": court,
                               "issue": fallback, "decision": "Unknown", "entities": {}}

                # Citations
                citations = []
                try:
                    async with httpx.AsyncClient(timeout=10.0) as cit_client:
                        citation_res = await cit_client.post(
                            f"{Config.CITATION_URL}/extract_citations",
                            json=CitationRequest(
                                case_id=case_id, case_text=case_text).dict(),
                            headers=auth_header
                        )
                        citation_res.raise_for_status()
                        citations = citation_res.json().get("citations", [])
                    logger.info(
                        f"Extracted {len(citations)} citations for {case_id}")
                except Exception as cit_err:
                    logger.error(
                        f"Citations failed for {case_id}: {str(cit_err)}")

                # Precedents
                related_precedents = []
                try:
                    async with httpx.AsyncClient(timeout=15.0) as prec_client:
                        precedent_res = await prec_client.post(
                            f"{Config.PRECEDENT_URL}/find_precedents",
                            json=PrecedentRequest(
                                case_id=case_id, citations=citations, case_text=case_text).dict(),
                            headers=auth_header
                        )
                        precedent_res.raise_for_status()
                        related_precedents = precedent_res.json().get("related_cases", [])
                    logger.info(
                        f"Found {len(related_precedents)} precedents for {case_id}")
                except Exception as prec_err:
                    logger.error(
                        f"Precedents failed for {case_id}: {str(prec_err)}")

                # Construct Case object
                cases.append(Case(
                    case_id=case_id,
                    title=case_name,
                    court=court,
                    decision=summary.get("decision", "Unknown"),
                    docket_id=case_data.get("docket_id", None),
                    date=case_data.get("date", None),
                    summary=summary,
                    legal_citations=citations,
                    citations_count=len(citations),
                    related_precedents=related_precedents
                ))

            logger.info(f"Orchestration complete: {len(cases)} enriched cases")
            return QueryResponse(
                cases=cases,
                case_type=search_req.case_type,
                topic=search_req.topic,
                date_from=search_req.date_from,
                date_to=search_req.date_to
            )
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
