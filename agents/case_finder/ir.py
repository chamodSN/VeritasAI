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
from sentence_transformers.util import cos_sim
from typing import Dict, Any, List
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException
from bs4 import BeautifulSoup
from datetime import datetime
from nltk.corpus import wordnet

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
                f"Limited results to {Config.MAX_RESULTS_PER_QUERY}")

        # --- Safe query building: No re-expansion; clean and quote ---
        def sanitize_query_part(part: str) -> str:
            if not part:
                return ""
            # Clean specials
            specials = r'[\+\-&|!(){}\[\]^~*?:\\/]'
            cleaned = re.sub(specials, r'\\\g<0>', part.strip())
            return cleaned

        # Use pre-expanded raw_query from parse_query
        raw_part = sanitize_query_part(request.raw_query or "")
        topic_part = sanitize_query_part(
            request.topic) if request.topic and request.topic != "unknown" else ""
        case_type_part = sanitize_query_part(
            request.case_type) if request.case_type and request.case_type != "unknown" else ""

        # Join with space (implicit AND in Lucene)
        query_parts = list(
            filter(None, [raw_part, topic_part, case_type_part]))
        search_query = " ".join(query_parts) or "legal cases"

        # Limit length
        if len(search_query) > 150:
            search_query = search_query[:150].rsplit(' ', 1)[0]

        # --- Call CourtListener API ---
        search_results = await courtlistener_api.search_cases(
            query=search_query,
            court=request.court or "",
            date_from=request.date_from,
            date_to=request.date_to,
            page_size=request.num_results
        )
        logger.info(
            f"Retrieved {len(search_results.get('results', []))} candidates")
        candidates = search_results.get("results", [])

        # --- Clean candidate text ---
        def clean_text(c):
            text = c.get('html_with_citations', '') or c.get(
                'plain_text', '') or c.get('snippet', '')[:500]
            if '<' in text:
                soup = BeautifulSoup(text, 'html.parser')
                text = soup.get_text()
            text = re.sub(r'\s+', ' ', text).strip()
            return f"{c.get('case_name', '')} {text} {c.get('snippet', '')}"

        qtext = f"{request.topic or ''} {request.raw_query or ''}".strip()
        query_embedding = embed_model.encode([qtext])[0]

        candidate_texts = [clean_text(c) for c in candidates]
        candidate_embeddings = embed_model.encode(candidate_texts)

        # --- Similarity scoring ---
        similarities = [
            (i, cos_sim(query_embedding, emb)[0][0].item())
            for i, emb in enumerate(candidate_embeddings)
        ]
        similarities.sort(key=lambda x: x[1], reverse=True)
        top_k = min(request.num_results, len(candidates))
        reranked_candidates = [candidates[i] for i, _ in similarities[:top_k]]

        # Filter by similarity threshold
        filtered_candidates = [c for i, c in enumerate(
            reranked_candidates) if similarities[i][1] >= 0.5]
        if not filtered_candidates:
            filtered_candidates = reranked_candidates[:top_k]

        # Filter by date
        new_filtered = []
        for idx, candidate in enumerate(filtered_candidates):
            date_filed_str = str(candidate.get('date_filed') or '')
            similarity = similarities[idx][1] if idx < len(
                similarities) else 0.0
            if similarity < 0.4:
                continue
            passes_date = True
            try:
                if request.date_from or request.date_to:
                    if date_filed_str and len(date_filed_str) >= 10:
                        case_date = datetime.strptime(
                            date_filed_str[:10], '%Y-%m-%d')
                        if request.date_from:
                            df = datetime.strptime(
                                request.date_from[:10], '%Y-%m-%d')
                            if case_date < df:
                                passes_date = False
                        if request.date_to and passes_date:
                            dt = datetime.strptime(
                                request.date_to[:10], '%Y-%m-%d')
                            if case_date > dt:
                                passes_date = False
                    else:
                        passes_date = False if request.date_from or request.date_to else True
            except Exception:
                passes_date = True
            if passes_date:
                new_filtered.append(candidate)

        filtered_candidates = new_filtered
        if not filtered_candidates:
            filtered_candidates = reranked_candidates[:top_k] if reranked_candidates else [
            ]

        # --- Construct Case objects ---
        cases = [
            Case(
                case_id=str(c.get("cluster_id", "")),
                title=c.get("case_name", ""),
                court=c.get("court", c.get("court_citation_string", None)),
                decision=c.get("disposition", None),
                docket_id=c.get("docket_number", None),
                date=str(c.get("date_filed", None))
            ).dict()
            for c in filtered_candidates
        ]

        # --- Optional bias detection ---
        if Config.ENABLE_BIAS_DETECTION:
            fairness_check = await responsible_ai.check_query_fairness(qtext)
            if not fairness_check.get("is_fair", True):
                logger.warning(
                    f"Query bias issue: {fairness_check.get('warnings', [])}")

        logger.info(f"Returning {len(cases)} cases")
        return SearchResponse(case_ids=[c['case_id'] for c in cases], hit_count=len(cases), cases=cases)

    except Exception as e:
        logger.error(f"Error retrieving cases: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cases/{cluster_id}")
async def get_case_by_id(cluster_id: str, token: dict = Depends(verify_token)) -> Dict[str, Any]:
    try:
        case_details = await courtlistener_api.get_case_details(cluster_id)
        if not case_details:
            raise HTTPException(status_code=404, detail="Case not found")
        logger.info(f"Case details for {cluster_id}")
        return case_details
    except Exception as e:
        logger.error(f"Error fetching case {cluster_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
