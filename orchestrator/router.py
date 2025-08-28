import requests
from common.models import QueryRequest, QueryResponse, Case
from common.config import Config
from common.logging import logger
from fastapi import HTTPException

async def process_query(request: QueryRequest) -> QueryResponse:
    logger.info(f"Processing query: {request.query}")
    # Step 1: Query Case Finder Agent
    case_finder_response = requests.post(f"{Config.CASE_FINDER_URL}/search", json={"query": request.query})
    if case_finder_response.status_code != 200:
        logger.error("Case Finder failed")
        raise HTTPException(status_code=500, detail="Case Finder failed")
    cases = [Case(**case) for case in case_finder_response.json()]
