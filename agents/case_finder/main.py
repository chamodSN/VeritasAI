from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from typing import List
import spacy
from spacy.matcher import Matcher
import httpx
from rapidfuzz import process
from sentence_transformers import SentenceTransformer, util
from common.security import verify_token
from common.logging import logger
from common.models import SearchRequest
from common.config import Config
from .utils import parse_dates_smart, normalize_text
from .ir import router as search_router

app = FastAPI(title="Query Understanding and Case Retrieval Agent")
app.include_router(search_router, prefix="/search", tags=["search"]) 

nlp = spacy.load("en_core_web_md")
embed_model = SentenceTransformer('all-MiniLM-L6-v2')

class QueryRequest(BaseModel):
    query: str

# Dynamic labels (sourced from API, with safe fallbacks)
CASE_TYPE_CANDIDATES: List[str] = ["criminal", "civil", "tax", "intellectual property", "contract", "labor", "family", "property", "bankruptcy"]
TOPIC_CANDIDATES: List[str] = [
    "cyber fraud", "data privacy", "theft", "contract dispute", "intellectual property",
    "bribery", "tax evasion", "employment discrimination", "breach of contract", "consumer protection",
]

@app.on_event("startup")
async def load_labels():
    global CASE_TYPE_CANDIDATES, TOPIC_CANDIDATES
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            if Config.CASE_TYPE_LABELS_URL:
                r = await client.get(Config.CASE_TYPE_LABELS_URL)
                if r.status_code == 200 and isinstance(r.json(), list) and r.json():
                    CASE_TYPE_CANDIDATES = [str(x).strip() for x in r.json() if str(x).strip()]
        except Exception as e:
            logger.warning(f"CASE_TYPE_LABELS_URL fetch failed, using defaults: {e}")
        try:
            if Config.TOPIC_LABELS_URL:
                r = await client.get(Config.TOPIC_LABELS_URL)
                if r.status_code == 200 and isinstance(r.json(), list) and r.json():
                    TOPIC_CANDIDATES = [str(x).strip() for x in r.json() if str(x).strip()]
        except Exception as e:
            logger.warning(f"TOPIC_LABELS_URL fetch failed, using defaults: {e}")


def classify_with_embeddings(text: str, candidates: List[str], min_score: float = 0.35) -> str:
    if not text or not candidates:
        return "unknown"
    q = embed_model.encode([text])[0]
    cands = embed_model.encode(candidates)
    sims = util.cos_sim(q, cands)[0].tolist()
    best_idx = max(range(len(sims)), key=lambda i: sims[i])
    best_score = sims[best_idx]
    return candidates[best_idx] if best_score >= min_score else "unknown"


def classify_with_fuzzy(text: str, candidates: List[str], min_score:int=80) -> str:
    if not text:
        return "unknown"
    match = process.extractOne(text, candidates, score_cutoff=min_score)
    return match[0] if match else "unknown"

@app.post("/parse_query", response_model=SearchRequest, tags=["parse"])
async def parse_query(request: QueryRequest, token: str = Depends(verify_token)):
    try:
        q = normalize_text(request.query)
        doc = nlp(q)

        # Dates (robust heuristics incl. relative/Q#)
        date_from, date_to = parse_dates_smart(q)

        # Candidate text for type/topic: noun chunks + query
        chunks = [chunk.text for chunk in doc.noun_chunks]
        bag = " ".join(chunks) if chunks else q

        # Two-stage classification: fuzzy (typo tolerant) → embeddings (semantic)
        case_type = classify_with_fuzzy(bag, CASE_TYPE_CANDIDATES) or "unknown"
        if case_type == "unknown":
            case_type = classify_with_embeddings(bag, CASE_TYPE_CANDIDATES)

        topic = classify_with_fuzzy(bag, TOPIC_CANDIDATES) or "unknown"
        if topic == "unknown":
            topic = classify_with_embeddings(bag, TOPIC_CANDIDATES)

        resp = SearchRequest(
            case_type=case_type,
            topic=topic,
            date_from=date_from,
            date_to=date_to,
            raw_query=q,
        )
        logger.info(f"Parsed query: {q} -> {resp.model_dump()}")
        return resp
    except Exception as e:
        logger.error(f"Error parsing query: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

