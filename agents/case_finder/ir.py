from common.responsible_ai import responsible_ai
from common.courtlistener_api import courtlistener_api
from common.config import Config
from common.models import SearchRequest, SearchResponse, Case
from common.logging import logger
from common.security import verify_token
import numpy as np
import httpx
import re
from sentence_transformers import SentenceTransformer
from typing import Dict, Any, List
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException

router = APIRouter()
embed_model = SentenceTransformer('all-MiniLM-L6-v2')


class SearchRequestExtended(SearchRequest):
    num_results: int = Field(10, description="Number of results to return")


@router.post("/search", response_model=SearchResponse)
async def search_cases(request: SearchRequestExtended, token: dict = Depends(verify_token)):
    try:
        if request.num_results > Config.MAX_RESULTS_PER_QUERY:
            request.num_results = Config.MAX_RESULTS_PER_QUERY
            logger.warning(
                f"RA Check: Limited results to {Config.MAX_RESULTS_PER_QUERY}")

        def sanitize_query_text(text: str) -> str:
            if not text:
                return ""
            cleaned = re.sub(r"[^\w\s.,!?]", " ", text)
            cleaned = re.sub(r"\s+", " ", cleaned).strip()[:150]
            return cleaned

        query_parts = [sanitize_query_text(request.raw_query or "")]
        if request.topic and request.topic != "unknown":
            query_parts.append(request.topic)
        if request.case_type and request.case_type != "unknown":
            query_parts.append(request.case_type)

        search_query = " ".join(filter(None, query_parts)) or "legal cases"

        try:
            search_results = await courtlistener_api.search_cases(
                query=search_query,
                court=request.court or "",
                date_from=request.date_from,
                date_to=request.date_to,
                page_size=request.num_results
            )
            logger.info(f"CourtListener raw response: {search_results}")
        except Exception as e:
            logger.warning(
                f"Primary search failed: {e}. Retrying with simplified query.")
            simplified_query = request.topic or "legal cases"
            search_results = await courtlistener_api.search_cases(
                query=simplified_query,
                court="",
                date_from=request.date_from,
                date_to=request.date_to,
                page_size=request.num_results
            )
            logger.info(f"CourtListener simplified response: {search_results}")

        candidates = search_results.get("results", [])
        logger.info(f"CourtListener returned {len(candidates)} candidates")

        if not candidates:
            return SearchResponse(case_ids=[], hit_count=0, cases=[])

        qtext = f"{request.topic or ''} {request.raw_query or ''}".strip()
        query_embedding = embed_model.encode([qtext])[0]

        candidate_texts = [
            f"{c.get('caseName', c.get('name', ''))} {c.get('text', '')} {c.get('snippet', '')}" for c in candidates]
        candidate_embeddings = embed_model.encode(candidate_texts)

        similarities = [
            (i, np.dot(query_embedding, emb) /
             (np.linalg.norm(query_embedding) * np.linalg.norm(emb)))
            for i, emb in enumerate(candidate_embeddings)
        ]
        similarities.sort(key=lambda x: x[1], reverse=True)
        top_k = min(request.num_results, len(candidates))
        reranked_candidates = [candidates[i] for i, _ in similarities[:top_k]]

        case_ids = [str(c.get("id", c.get("cluster_id", "")))
                    for c in reranked_candidates]
        cases = [
            Case(
                case_id=str(c.get("id", c.get("cluster_id", ""))),
                title=c.get("caseName", c.get("name", "")),
                court=c.get("court_citation_string",
                            c.get("court_name", None)),
                decision=c.get("disposition", c.get("status", None)),
                docket_id=c.get("docketNumber", c.get("docket_number", None))
            ).dict()
            for c in reranked_candidates
        ]

        diversity_check = await responsible_ai.check_result_diversity(cases)
        relevance_check = await responsible_ai.check_result_relevance(qtext, cases)

        if not diversity_check.get("is_diverse", True):
            logger.warning(
                f"RA Check: Low diversity - {diversity_check.get('recommendations', [])}")
        if not relevance_check.get("is_relevant", True):
            logger.warning(
                f"RA Check: Low relevance - avg_relevance: {relevance_check.get('relevance_score', 0)}")

        logger.info(f"Returning {len(case_ids)} case IDs")
        return SearchResponse(case_ids=case_ids, hit_count=len(case_ids), cases=cases)

    except Exception as e:
        logger.error(f"Error retrieving cases: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cases/{cluster_id}")
async def get_case_by_id(cluster_id: str, token: dict = Depends(verify_token)) -> Dict[str, Any]:
    try:
        case_details = await courtlistener_api.get_case_details(cluster_id)
        if not case_details:
            raise HTTPException(status_code=404, detail="Case not found")
        logger.info(f"Case details for {cluster_id}: {case_details}")
        return case_details
    except Exception as e:
        logger.error(f"Error fetching case {cluster_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
