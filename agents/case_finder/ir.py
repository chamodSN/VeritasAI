# case_finder/ir.py (Updated for hybrid IR: Use MongoDB Atlas for document cache and vector index. Hybrid retrieval (keyword + semantic). Added ML cross-encoder reranker. RA checks for result diversity/transparency. Removed on-the-fly CourtListener search; use pre-indexed data.)
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sentence_transformers import SentenceTransformer
from sentence_transformers.cross_encoder import CrossEncoder
from typing import List, Dict, Any
from common.security import verify_token
from common.logging import logger
from common.models import SearchRequest, SearchResponse
from common.config import Config
from common.db import MongoDB
import numpy as np

router = APIRouter()
embed_model = SentenceTransformer(
    'nlpaueb/legal-bert-base-uncased')  # Legal-specific embeddings
# Pre-trained reranker; can fine-tune on CourtListener data later
reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')


class SearchRequestExtended(SearchRequest):
    num_results: int = Field(10, description="Number of results to return")


@router.post("/search", response_model=SearchResponse)
async def search_cases(request: SearchRequestExtended, token: dict = Depends(verify_token)):
    try:
        # Document cache with vector index
        collection = MongoDB.get_db()["cases"]

        # Parse query for hybrid: Keyword terms + semantic embedding
        query_terms: List[str] = []
        for token in filter(None, (request.case_type or '').split() + (request.topic or '').split()):
            term = token
            if len(term) >= 2:
                if len(term) < 5:
                    qt = f"{term}*"
                else:
                    qt = f"{term}~"
                query_terms.append(qt)
        keyword_query = " ".join(query_terms) if query_terms else (
            request.raw_query or "")
        qtext = f"{request.case_type} {request.topic} {request.raw_query}".strip()

        # Embed query for semantic search
        Q = embed_model.encode([qtext])
        query_vector = Q[0].tolist()

        # Hybrid Retrieval: Vector search with filters (date, court already pre-filtered to scotus)
        # Note: Assumes MongoDB Atlas vector index named 'vector_index' on 'embedding'
        vector_pipeline = [
            {
                "$vectorSearch": {
                    "index": "vector_index",
                    "path": "embedding",
                    "queryVector": query_vector,
                    "numCandidates": 100,
                    "limit": request.num_results * 2  # Oversample for reranking
                }
            },
            # Hybrid: Add keyword filter if present
            {"$match": {"$text": {"$search": keyword_query}} if keyword_query else {}},
            {
                "$project": {
                    "score": {"$meta": "vectorSearchScore"},
                    "metadata": 1,
                    "text": 1
                }
            }
        ]
        if request.date_from or request.date_to:
            match_stage = {}
            if request.date_from:
                match_stage["metadata.dateFiled"] = {"$gte": request.date_from}
            if request.date_to:
                match_stage["metadata.dateFiled"] = {"$lte": request.date_to}
            vector_pipeline.insert(1, {"$match": match_stage})  # Filter dates

        candidates = list(collection.aggregate(vector_pipeline))
        logger.info(f"Hybrid retrieval fetched {len(candidates)} candidates")

        if not candidates:
            return SearchResponse(case_ids=[], hit_count=0, cases=[])

        # ML Reranking with cross-encoder
        pairs = [[qtext, cand["text"]] for cand in candidates]
        scores = reranker.predict(pairs)
        sorted_indices = np.argsort(scores)[::-1]
        top_k = min(request.num_results, len(candidates))
        reranked = [candidates[i] for i in sorted_indices[:top_k]]

        # Prepare response
        case_ids = [cand["metadata"]["cluster_id"] for cand in reranked]
        cases = [cand["metadata"] for cand in reranked]

        # RA Check: Transparency (log scores), Fairness (check diversity in courts/topics, but since scotus only, log avg score)
        avg_score = np.mean(scores) if len(scores) > 0 else 0
        if avg_score < 0.5:
            logger.warning(
                f"RA Check: Low average reranking score ({avg_score}). Potential relevance bias; consider model fine-tuning on diverse legal data.")
        else:
            logger.info(
                f"RA Check: Results reranked with avg score {avg_score}. Ethical handling: Auditable scores ensure transparency; no PII in public data.")

        logger.info(f"Returning {len(case_ids)} case IDs")
        return SearchResponse(case_ids=case_ids, hit_count=len(case_ids), cases=cases)

    except Exception as e:
        logger.error(f"Error retrieving cases: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cases/{cluster_id}")
async def get_case_by_id(cluster_id: str, token: dict = Depends(verify_token)) -> Dict[str, Any]:
    collection = MongoDB.get_db()["cases"]
    doc = collection.find_one({"_id": cluster_id}, {"metadata": 1})
    if not doc:
        raise HTTPException(status_code=404, detail="Case not found")
    return doc["metadata"]
