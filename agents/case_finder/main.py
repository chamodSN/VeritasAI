from fastapi import FastAPI, Request
from pydantic import BaseModel
from typing import List
import json
from common.http import verify_request, error_response
from .ir import search_cases
from .models import CaseDoc

app = FastAPI()


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5


@app.post("/search")
async def search(req: SearchRequest, request: Request):
    body = await request.body()
    # if not verify_request("POST", "/search", body.decode(), request.headers):
    # return error_response("UNAUTHORIZED", "Invalid signature")

    results: List[CaseDoc] = await search_cases(req.query, req.top_k)
    return {"results": [r.dict() for r in results]}
