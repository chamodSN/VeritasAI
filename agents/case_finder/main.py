from fastapi import FastAPI, Depends
from common.security import api_key_header, verify_token, limiter
from common.models import QueryRequest, Case
from agents.case_finder.ir import search_cases
from common.logging import logger

app = FastAPI(title="Case Finder Agent")
app.state.limiter = limiter

@app.post("/search", response_model=list[Case])
@limiter.limit("10/minute")
async def search(request: QueryRequest, token: str = Depends(api_key_header)):
    logger.info(f"Case Finder search: {request.query}")
    verify_token(token)
    return search_cases(request.query)