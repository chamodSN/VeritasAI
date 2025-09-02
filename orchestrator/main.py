from fastapi import FastAPI, Depends
from common.security import api_key_header, verify_token, limiter
from orchestrator.router import process_query
from common.models import QueryRequest, QueryResponse
from common.logging import logger

app = FastAPI(title="Legal Case Researcher Orchestrator")
app.state.limiter = limiter


@app.post("/query", response_model=QueryResponse)
@limiter.limit("5/minute")
async def query_cases(request: QueryRequest, token: str = Depends(api_key_header)):
    logger.info(f"Query received: {request.query}")
    verify_token(token)
    return await process_query(request)
