import httpx
import language_tool_python
from common.models import *
from common.config import Config
from common.logging import logger
from common.db import MongoDB
from fastapi import HTTPException
from starlette.requests import Request  # Ensure this import is present
from common.models import PrecedentRequest, PrecedentResponse

tool = language_tool_python.LanguageTool('en-US')


async def process_query(request: QueryRequest, token: dict, request_obj: Request) -> QueryResponse:
    user_id = token.get("sub")
    query = request.query

    # Grammar correction
    matches = tool.check(query)
    corrected_query = language_tool_python.utils.correct(query, matches)
    logger.info(f"Corrected query: {corrected_query}")

    # Check cache
    cached = await MongoDB.get_query_result(user_id, corrected_query)
    if cached:
        logger.info("Cache hit")
        return QueryResponse(**cached["results"])

    # Get full Authorization header from incoming request
    auth_header = request_obj.headers.get("authorization")
    if not auth_header:
        raise HTTPException(
            status_code=401, detail="Missing Authorization header")

    async with httpx.AsyncClient(timeout=30) as client:
        # Parse query
        parse_res = await client.post(
            f"{Config.CASE_FINDER_URL}/parse_query",
            json={"query": corrected_query},
            headers={"Authorization": auth_header}  # Propagate full header
        )
        parse_res.raise_for_status()
        search_req = SearchRequest(**parse_res.json())

        # Search cases
        search_res = await client.post(
            f"{Config.CASE_FINDER_URL}/search",
            json=search_req.model_dump() | {"num_results": 5},
            headers={"Authorization": auth_header}  # Propagate full header
        )
        search_res.raise_for_status()
        search_result = SearchResponse(**search_res.json())
        cases_data = search_result.cases[:5]  # Top 5 for speed

        # Parallel: Summarize + Citations + Precedents
        summaries, citations, precedents = [], [], []
        for case_data in cases_data:
            # From API: opinions have "id"
            case_id = str(case_data["cluster_id"])

            # Summary
            sum_res = await client.post(
                f"{Config.SUMMARY_URL}/summarize",
                json={"case_id": case_id, "case_data": case_data},
                headers={"Authorization": auth_header}  # Propagate full header
            )
            sum_res.raise_for_status()
            summaries.append(SummaryResponse(**sum_res.json()).summary)

            # Citations
            cit_res = await client.post(
                f"{Config.CITATION_URL}/extract_citations",
                json={"case_id": case_id, "case_data": case_data},
                headers={"Authorization": auth_header}  # Propagate full header
            )
            cit_res.raise_for_status()
            cit_list = CitationResponse(**cit_res.json()).citations
            citations.append(cit_list)

            # Precedents
            prec_res = await client.post(
                f"{Config.PRECEDENT_URL}/find_precedents",
                json={"case_id": case_id, "citations": cit_list},
                headers={"Authorization": auth_header}  # Propagate full header
            )
            prec_res.raise_for_status()
            precedents.append(PrecedentResponse(
                **prec_res.json()).related_cases)

        # Format response
        cases = []
        for i, case_data in enumerate(cases_data):
            cases.append(Case(
                case_id=str(case_data["cluster_id"]),
                case_name=case_data.get("case_name", "Unknown"),
                court=case_data.get("court", "Unknown"),
                decision=case_data.get("disposition", "Unknown"),
                summary=summaries[i],
                citations=citations[i],
                related_precedents=precedents[i]
            ))

        response = QueryResponse(cases=cases)
        await MongoDB.store_query_result(user_id, corrected_query, response.model_dump())
        return response
