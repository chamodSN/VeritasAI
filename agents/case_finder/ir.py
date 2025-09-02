
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
import httpx
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
from typing import List, Dict, Any, Optional
from common.security import verify_token
from common.logging import logger
from common.config import Config
from common.models import SearchRequest, CachedSearch
from .cache import set_search_result, get_search_result, make_search_key, set_case, get_case

router = APIRouter()

model = SentenceTransformer('all-MiniLM-L6-v2')  # Global model


class SearchResponse(BaseModel):
    cache_key: str = Field(...,
                           description="Key where the result set is cached for other agents")
    case_ids: List[str] = Field(default_factory=list)
    hit_count: int = 0


class SearchRequestExtended(SearchRequest):  # Extend for optional limit
    num_results: int = Field(10, description="Number of results to return")


@router.post("/search", response_model=SearchResponse)
async def search_cases(request: SearchRequestExtended, token: str = Depends(verify_token)):
    try:
        cache_key = make_search_key(
            request.case_type, request.topic, request.date_from, request.date_to)
        cached = get_search_result(cache_key)
        if cached:
            logger.info(
                f"Cache hit for {cache_key} -> {len(cached['case_ids'])} cases")
            return SearchResponse(cache_key=cache_key, case_ids=cached['case_ids'], hit_count=len(cached['case_ids']))

        # Build fuzzy query for CourtListener (Lucene-like)
        query_terms: List[str] = []
        for token in filter(None, (request.case_type or '').split() + (request.topic or '').split()):
            term = token
            if len(term) >= 2:
                # fuzzy + wildcard for short tokens
                qt = f"{term}~"
                if len(term) < 5:
                    qt += "*"
                query_terms.append(qt)
        query = " AND ".join(query_terms) if query_terms else (
            request.raw_query or "")

        params: Dict[str, Any] = {"q": query, "type": "o"}  # opinions
        if request.date_from:
            params["date_filed_after"] = request.date_from
        if request.date_to:
            params["date_filed_before"] = request.date_to

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
            set_search_result(
                cache_key, {"request": request.model_dump(), "case_ids": [], "cases": []})
            return SearchResponse(cache_key=cache_key, case_ids=[], hit_count=0)

        # Rerank with FAISS on (caseName + first-opinion snippet)
        dim = 384
        index = faiss.IndexFlatL2(dim)
        embeddings = []
        case_ids: List[str] = []
        texts: List[str] = []

        for c in cases:
            opinions = c.get('opinions', [])
            snippet = opinions[0].get('snippet', '') if opinions else ''
            text = f"{c.get('caseName', '')} {snippet}".strip()
            texts.append(text)
            case_ids.append(str(c.get("cluster_id")))

        if texts:
            X = model.encode(texts)
            X = np.asarray(X, dtype='float32')
            index.add(X)
            qtext = f"{request.case_type} {request.topic}".strip() or (
                request.raw_query or "")
            Q = model.encode([qtext]).astype('float32')
            k = min(request.num_results, len(texts))
            D, I = index.search(Q, k)
            reranked_ids = [case_ids[i] for i in I[0]]
        else:
            reranked_ids = case_ids

        # Persist to shared cache for other agents (includes full case payloads)
        bundle = {"request": request.model_dump(
        ), "case_ids": reranked_ids, "cases": cases}
        set_search_result(cache_key, bundle)
        for c in cases:
            cid = str(c.get("cluster_id"))
            if cid:
                set_case(cid, c)

        logger.info(
            f"Processed + cached {len(reranked_ids)} case IDs under {cache_key}")
        return SearchResponse(cache_key=cache_key, case_ids=reranked_ids, hit_count=len(reranked_ids))
    except httpx.HTTPStatusError as he:
        logger.error(
            f"CourtListener error: {he.response.status_code} {he.response.text}")
        raise HTTPException(status_code=he.response.status_code,
                            detail="Upstream API error")
    except Exception as e:
        logger.error(f"Error retrieving cases: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# --- Convenience endpoints for other agents to consume cached data ---


@router.get("/cache/search/{cache_key}", response_model=CachedSearch)
async def get_cached_search(cache_key: str, token: str = Depends(verify_token)):
    payload = get_search_result(cache_key)
    if not payload:
        raise HTTPException(status_code=404, detail="Cache miss")
    return CachedSearch(key=cache_key, request=SearchRequest(**payload["request"]), result_case_ids=payload["case_ids"], cases=payload["cases"])


@router.get("/cases/{cluster_id}")
async def get_case_by_id(cluster_id: str, token: str = Depends(verify_token)) -> Dict[str, Any]:
    cached = get_case(cluster_id)
    if cached:
        return cached
    # Fallback: fetch from API and then cache it
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
        set_case(cluster_id, data)
        return data
