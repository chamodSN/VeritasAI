from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
import asyncio
import numpy as np
from sentence_transformers import SentenceTransformer
from common.security import verify_token
from common.logging import logger
from common.config import Config
from common.courtlistener_api import courtlistener_api
from common.models import PrecedentRequest, PrecedentResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Precedent Finding Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

try:
    embed_model = SentenceTransformer('all-MiniLM-L6-v2')
    logger.info("SentenceTransformer model loaded")
except Exception as e:
    logger.error(f"Failed to load SentenceTransformer: {str(e)}")
    embed_model = None


class PrecedentRequestExtended(PrecedentRequest):
    max_results: int = 5
    similarity_threshold: float = 0.4


def calculate_semantic_similarity(text1: str, text2: str) -> float:
    if not embed_model:
        logger.warning(
            "SentenceTransformer not loaded, returning 0.0 similarity")
        return 0.0
    try:
        embeddings = embed_model.encode([text1, text2])
        return float(np.dot(embeddings[0], embeddings[1]) / (np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1])))
    except Exception as e:
        logger.error(f"Error calculating similarity: {str(e)}")
        return 0.0


async def find_similar_cases_by_citations(case_id: str, citations: List[str], max_results: int = 5) -> List[Dict[str, Any]]:
    try:
        similar_cases = []
        for citation in citations[:3]:  # Limit for performance
            search_results = await courtlistener_api.search_cases(query=citation, court="", page_size=5)
            logger.info(
                f"Search results for citation {citation}: {search_results}")
            for result in search_results.get("results", []):
                if str(result.get("cluster_id")) != case_id:
                    similar_cases.append(result)
        unique_cases = []
        seen_ids = set()
        for case in similar_cases:
            case_id_val = str(case.get("cluster_id"))
            if case_id_val and case_id_val not in seen_ids:
                unique_cases.append(case)
                seen_ids.add(case_id_val)
                if len(unique_cases) >= max_results:
                    break
        return unique_cases
    except Exception as e:
        logger.error(f"Error finding similar cases by citations: {str(e)}")
        return []


async def find_similar_cases_by_content(case_id: str, case_text: str, max_results: int = 5, similarity_threshold: float = 0.4) -> List[Dict[str, Any]]:
    if not case_text:
        logger.warning("Empty case text provided for content-based search")
        return []
    try:
        search_query = " ".join(case_text.split()[:30])  # Use first 30 words
        search_results = await courtlistener_api.search_cases(query=search_query, court="", page_size=10)
        logger.info(f"Search results for content query: {search_results}")
        candidates = search_results.get("results", [])
        if not candidates:
            return []
        similar_cases = []
        for candidate in candidates:
            if str(candidate.get("cluster_id")) == case_id:
                continue
            candidate_text = f"{candidate.get('caseName', '')} {candidate.get('text', '')}"
            similarity = calculate_semantic_similarity(
                case_text, candidate_text)
            if similarity >= similarity_threshold:
                candidate["similarity_score"] = similarity
                similar_cases.append(candidate)
        similar_cases.sort(key=lambda x: x.get(
            "similarity_score", 0), reverse=True)
        return similar_cases[:max_results]
    except Exception as e:
        logger.error(f"Error finding similar cases by content: {str(e)}")
        return []


@app.post("/find_precedents", response_model=PrecedentResponse)
async def find_precedents(request: PrecedentRequestExtended, token: dict = Depends(verify_token)):
    logger.info(f"Received precedent request for case_id {request.case_id}")
    try:
        if not request.case_id:
            logger.warning(f"Invalid case_id {request.case_id}")
            return PrecedentResponse(related_cases=[])
        if request.max_results > Config.MAX_RESULTS_PER_QUERY:
            request.max_results = Config.MAX_RESULTS_PER_QUERY
            logger.warning(
                f"RA Check: Limited results to {Config.MAX_RESULTS_PER_QUERY}")
        case_text = await courtlistener_api.get_case_text(request.case_id)
        if not case_text:
            logger.warning(f"No case text for case_id {request.case_id}")
        similar_cases_citations = await find_similar_cases_by_citations(request.case_id, request.citations, request.max_results // 2)
        similar_cases_content = await find_similar_cases_by_content(request.case_id, case_text, request.max_results // 2, request.similarity_threshold)
        unique_cases = []
        seen_ids = set()
        for case in similar_cases_citations + similar_cases_content:
            case_id_val = str(case.get("cluster_id"))
            if case_id_val and case_id_val not in seen_ids:
                unique_cases.append(case)
                seen_ids.add(case_id_val)
                if len(unique_cases) >= request.max_results:
                    break
        formatted_cases = [
            {
                "id": str(case.get("cluster_id", "")),
                "title": case.get("caseName", "Unknown"),
                "court": case.get("court_citation_string", "Unknown"),
                "date": case.get("dateFiled", "")
            }
            for case in unique_cases
        ]
        logger.info(
            f"Found {len(formatted_cases)} similar cases for case {request.case_id}")
        return PrecedentResponse(related_cases=formatted_cases)
    except Exception as e:
        logger.error(
            f"Error finding precedents for case {request.case_id}: {str(e)}")
        return PrecedentResponse(related_cases=[])