from .ir import router as ir_router
from fastapi.middleware.cors import CORSMiddleware
from common.responsible_ai import responsible_ai
from common.config import Config
from common.models import SearchRequest
from common.logging import logger
from common.security import verify_token
import numpy as np
from sentence_transformers import SentenceTransformer
from rapidfuzz import process
import httpx
import spacy
from typing import List, Tuple
from pydantic import BaseModel
from fastapi import FastAPI, Depends, HTTPException

app = FastAPI(title="Query Understanding Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ir_router, tags=["search"])

nlp = spacy.load("en_core_web_sm")
embed_model = SentenceTransformer('all-MiniLM-L6-v2')

CASE_TYPE_CANDIDATES = []
TOPIC_CANDIDATES = []


async def load_labels():
    global CASE_TYPE_CANDIDATES, TOPIC_CANDIDATES
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            r = await client.get(Config.CASE_TYPE_LABELS_URL)
            r.raise_for_status()
            CASE_TYPE_CANDIDATES = [str(x).strip().lower()
                                    for x in r.json() if str(x).strip()]
            logger.info(
                f"Loaded {len(CASE_TYPE_CANDIDATES)} case types from {Config.CASE_TYPE_LABELS_URL}")
        except Exception as e:
            logger.error(
                f"Failed to load case types from {Config.CASE_TYPE_LABELS_URL}: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Failed to load case types: {str(e)}")
        try:
            r = await client.get(Config.TOPIC_LABELS_URL)
            r.raise_for_status()
            TOPIC_CANDIDATES = [str(x).strip().lower()
                                for x in r.json() if str(x).strip()]
            logger.info(
                f"Loaded {len(TOPIC_CANDIDATES)} topics from {Config.TOPIC_LABELS_URL}")
        except Exception as e:
            logger.error(
                f"Failed to load topics from {Config.TOPIC_LABELS_URL}: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Failed to load topics: {str(e)}")


@app.on_event("startup")
async def startup_event():
    await load_labels()


def classify_with_embeddings(text: str, candidates: List[str], min_score: float = 0.4) -> Tuple[str, float]:
    if not text or not candidates:
        return "unknown", 0.0
    try:
        q = embed_model.encode([text])[0]
        cands = embed_model.encode(candidates)
        sims = [q @ c / (np.linalg.norm(q) * np.linalg.norm(c)) for c in cands]
        best_idx = max(range(len(sims)), key=lambda i: sims[i])
        best_score = sims[best_idx]
        return candidates[best_idx] if best_score >= min_score else "unknown", best_score
    except Exception as e:
        logger.error(f"Error in embedding classification: {str(e)}")
        return "unknown", 0.0


def classify_with_fuzzy(text: str, candidates: List[str], min_score: int = 70) -> Tuple[str, float]:
    if not text or not candidates:
        return "unknown", 0.0
    try:
        result = process.extractOne(text, candidates, score_cutoff=min_score)
        return (result[0], result[1] / 100.0) if result else ("unknown", 0.0)
    except Exception as e:
        logger.error(f"Error in fuzzy classification: {str(e)}")
        return "unknown", 0.0


@app.post("/parse_query", response_model=SearchRequest, tags=["parse"])
async def parse_query(request: SearchRequest, token: dict = Depends(verify_token)):
    try:
        if len(request.raw_query or "") > Config.MAX_QUERY_LENGTH:
            raise HTTPException(
                status_code=400, detail=f"Query too long. Max: {Config.MAX_QUERY_LENGTH} chars")

        fairness_check = await responsible_ai.check_query_fairness(request.raw_query or "")
        if not fairness_check.get("is_fair", True):
            logger.warning(
                f"RA Check: Query fairness issue - {fairness_check.get('warnings', [])}")

        q = (request.raw_query or "").lower()
        doc = nlp(q)
        from .utils import parse_dates_smart
        date_from, date_to = parse_dates_smart(q)

        chunks = [chunk.text for chunk in doc.noun_chunks]
        bag = " ".join(chunks) if chunks else q

        case_type, fuzzy_score = classify_with_fuzzy(bag, CASE_TYPE_CANDIDATES)
        if case_type == "unknown":
            case_type, embed_score = classify_with_embeddings(
                bag, CASE_TYPE_CANDIDATES)
            score = embed_score
        else:
            score = fuzzy_score

        topic, topic_fuzzy_score = classify_with_fuzzy(bag, TOPIC_CANDIDATES)
        if topic == "unknown":
            topic, topic_embed_score = classify_with_embeddings(
                bag, TOPIC_CANDIDATES)
            topic_score = topic_embed_score
        else:
            topic_score = topic_fuzzy_score

        classifications = {"case_type": (
            case_type, score), "topic": (topic, topic_score)}
        confidence_check = await responsible_ai.check_classification_confidence(classifications)
        if not confidence_check.get("is_confident", True):
            logger.warning(
                f"RA Check: Low confidence - {confidence_check.get('confidence_issues', [])}")

        resp = SearchRequest(
            case_type=case_type,
            topic=topic,
            date_from=date_from or request.date_from,
            date_to=date_to or request.date_to,
            raw_query=q,
            court=request.court,
            page=request.page,
            per_page=request.per_page
        )
        logger.info(f"Parsed query: {q} -> {resp.model_dump()}")
        return resp
    except Exception as e:
        logger.error(f"Error parsing query: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
