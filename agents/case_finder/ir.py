# case_finder/ir.py (Updated to handle court parameter in search)
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
import httpx
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
from typing import List, Dict, Any
from common.security import verify_token
from common.logging import logger
from common.models import SearchRequest, SearchResponse
from common.config import Config

router = APIRouter()
model = SentenceTransformer('all-MiniLM-L6-v2',
                            device='cpu')


class SearchRequestExtended(SearchRequest):
    num_results: int = Field(10, description="Number of results to return")


@router.post("/search", response_model=SearchResponse)
async def search_cases(request: SearchRequestExtended, token: dict = Depends(verify_token)):
    try:
        query_terms: List[str] = []
        for token in filter(None, (request.case_type or '').split() + (request.topic or '').split()):
            term = token
            if len(term) >= 2:
                if len(term) < 5:
                    qt = f"{term}*"
                else:
                    qt = f"{term}~"
                query_terms.append(qt)
        query = " AND ".join(query_terms) if query_terms else (
            request.raw_query or "")

        params: Dict[str, Any] = {"q": query, "type": "o"}
        if request.date_from:
            params["date_filed_min"] = request.date_from
        if request.date_to:
            params["date_filed_max"] = request.date_to
        if request.court:
            params["court"] = request.court

        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(
                f"{Config.COURTLISTENER_BASE_URL}search/",
                params=params,
                headers={
                    "Authorization": f"Token {Config.COURTLISTENER_API_KEY}"} if Config.COURTLISTENER_API_KEY else None,
            )
            r.raise_for_status()
            cases: List[Dict[str, Any]] = r.json().get("results", [])
            logger.info(f"Fetched {len(cases)} cases from CourtListener")

        if not cases:
            return SearchResponse(case_ids=[], hit_count=0, cases=[])

        dim = 384
        index = faiss.IndexFlatL2(dim)
        texts, case_ids = [], []
        for c in cases:
            opinions = c.get('opinions', [])
            snippet = opinions[0].get('snippet', '') if opinions else ''
            text = f"{c.get('caseName', '')} {snippet}".strip()
            texts.append(text)
            case_ids.append(str(c.get("cluster_id")))

        if texts:
            X = model.encode(texts)
            X = np.array(X)
            X /= np.linalg.norm(X, axis=1, keepdims=True)
            X = X.astype('float32')
            index.add(X)
            qtext = f"{request.case_type} {request.topic}".strip() or (
                request.raw_query or "")
            Q = model.encode([qtext])
            Q = np.array(Q)
            Q /= np.linalg.norm(Q, axis=1, keepdims=True)
            Q = Q.astype('float32')
            k = min(request.num_results, len(texts))
            _, I = index.search(Q, k)
            reranked_ids = [case_ids[i] for i in I[0]]
            reranked_cases = [c for c in cases if str(
                c.get("cluster_id")) in reranked_ids]
        else:
            reranked_ids = case_ids
            reranked_cases = cases

        logger.info(f"Returning {len(reranked_ids)} case IDs")
        return SearchResponse(case_ids=reranked_ids, hit_count=len(reranked_ids), cases=reranked_cases)

    except httpx.HTTPStatusError as he:
        logger.error(
            f"CourtListener error: {he.response.status_code} {he.response.text}")
        raise HTTPException(status_code=he.response.status_code,
                            detail="Upstream API error")
    except Exception as e:
        logger.error(f"Error retrieving cases: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cases/{cluster_id}")
async def get_case_by_id(cluster_id: str, token: dict = Depends(verify_token)) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(
            f"{Config.COURTLISTENER_BASE_URL}clusters/{cluster_id}/",
            headers={
                "Authorization": f"Token {Config.COURTLISTENER_API_KEY}"} if Config.COURTLISTENER_API_KEY else None,
        )
        if r.status_code != 200:
            raise HTTPException(status_code=r.status_code,
                                detail="Case not found")
        data = r.json()
        return data
