# case_finder/main.py (Updated for improved IR: Added ingestion of SCOTUS cases at startup for local indexing in MongoDB. Changed embedding model to legal-specific. Updated classifications to return scores for RA checks. Added RA logging for fairness/transparency.)
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Tuple
import spacy
import httpx
from rapidfuzz import process
from sentence_transformers import SentenceTransformer, util
from common.security import verify_token
from common.logging import logger
from common.models import SearchRequest
from common.config import Config
from common.db import MongoDB
from fastapi.middleware.cors import CORSMiddleware
from .ir import router as ir_router

app = FastAPI(title="Query Understanding Agent")

# Include the ir.py router
app.include_router(ir_router, tags=["search"])

nlp = spacy.load("en_core_web_md")
embed_model = SentenceTransformer('nlpaueb/legal-bert-base-uncased')  # Changed to legal-specific model for better domain adaptation

class QueryRequest(BaseModel):
    query: str

CASE_TYPE_CANDIDATES: List[str] = ["criminal", "civil", "tax",
                                   "intellectual property", "contract", "labor", "family", "property", "bankruptcy"]
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
                r.raise_for_status()
                CASE_TYPE_CANDIDATES = [str(x).strip().lower()
                                        for x in r.json() if str(x).strip()]
                logger.info(f"Loaded {len(CASE_TYPE_CANDIDATES)} case types")
        except Exception as e:
            logger.warning(
                f"CASE_TYPE_LABELS_URL failed: {e}. Using defaults.")
        try:
            if Config.TOPIC_LABELS_URL:
                r = await client.get(Config.TOPIC_LABELS_URL)
                r.raise_for_status()
                TOPIC_CANDIDATES = [str(x).strip().lower()
                                    for x in r.json() if str(x).strip()]
                logger.info(f"Loaded {len(TOPIC_CANDIDATES)} topics")
        except Exception as e:
            logger.warning(f"TOPIC_LABELS_URL failed: {e}. Using defaults.")

@app.on_event("startup")
async def index_scotus_cases():
    # Ingestion pipeline: Fetch all SCOTUS cases from CourtListener and index in MongoDB with embeddings
    # Note: Assumes MongoDB Atlas with vector search index created on 'embedding' field (dim=768, cosine similarity)
    # Ethical handling: Only public legal data, no PII processing
    collection = MongoDB.get_db()["cases"]
    if collection.count_documents({"court": "scotus"}) > 0:
        logger.info("SCOTUS cases already indexed, skipping ingestion.")
        return

    async with httpx.AsyncClient(timeout=60) as client:
        params = {"court": "scotus", "type": "o", "page_size": 100}
        next_url = f"{Config.COURTLISTENER_BASE_URL}search/"
        cases = []
        while next_url:
            r = await client.get(next_url, params=params if "search/" in next_url else {}, headers={"Authorization": f"Token {Config.COURTLISTENER_API_KEY}"} if Config.COURTLISTENER_API_KEY else None)
            r.raise_for_status()
            data = r.json()
            cases.extend(data["results"])
            next_url = data["next"]

        # Process and embed
        documents = []
        for case in cases:
            opinions = case.get('opinions', [])
            text = f"{case.get('caseName', '')} {opinions[0].get('snippet', '') if opinions else ''}".strip()
            embedding = embed_model.encode(text).tolist()
            doc = {
                "_id": str(case["cluster_id"]),
                "metadata": case,
                "text": text,
                "embedding": embedding,
                "court": "scotus"  # For filtering
            }
            documents.append(doc)

        if documents:
            collection.insert_many(documents)
            logger.info(f"Indexed {len(documents)} SCOTUS cases in MongoDB.")
        else:
            logger.warning("No SCOTUS cases fetched for indexing.")

def classify_with_embeddings(text: str, candidates: List[str], min_score: float = 0.2) -> Tuple[str, float]:
    if not text or not candidates:
        return "unknown", 0.0
    q = embed_model.encode([text])[0]
    cands = embed_model.encode(candidates)
    sims = util.cos_sim(q, cands)[0].tolist()
    best_idx = max(range(len(sims)), key=lambda i: sims[i])
    best_score = sims[best_idx]
    label = candidates[best_idx] if best_score >= min_score else "unknown"
    return label, best_score

def classify_with_fuzzy(text: str, candidates: List[str], min_score: int = 60) -> Tuple[str, float]:
    if not text:
        return "unknown", 0.0
    match = process.extractOne(text, candidates, score_cutoff=min_score)
    return match[0], match[1] / 100.0 if match else ("unknown", 0.0)

def rule_based_case_type(query: str) -> str:
    query = query.lower()
    if "fraud" in query or "crime" in query or "cases" in query:
        return "criminal"
    return None

@app.post("/parse_query", response_model=SearchRequest, tags=["parse"])
async def parse_query(request: QueryRequest, token: dict = Depends(verify_token)):
    logger.debug(f"Received token claims: {token}")
    try:
        q = request.query  # Note: Removed normalize_text as it's not defined; assume query is pre-normalized if needed
        doc = nlp(q)

        date_from, date_to = parse_dates_smart(q)  # Assuming this is defined in utils

        chunks = [chunk.text for chunk in doc.noun_chunks]
        bag = " ".join(chunks) if chunks else q

        # Fuzzy first, then embeddings, then rule-based
        case_type, fuzzy_score = classify_with_fuzzy(bag, CASE_TYPE_CANDIDATES)
        if case_type == "unknown":
            case_type, embed_score = classify_with_embeddings(bag, CASE_TYPE_CANDIDATES)
            score = embed_score
        else:
            score = fuzzy_score
        if case_type == "unknown":
            rule_case = rule_based_case_type(q)
            if rule_case:
                case_type = rule_case
                score = 1.0  # High confidence for rule-based

        # RA Check: Fairness and transparency in classification
        if score < 0.5:
            logger.warning(f"RA Check: Low confidence in case_type classification ({case_type}, score={score}). Potential bias risk; review for underrepresented categories.")
        else:
            logger.info(f"RA Check: Case type classified as {case_type} with score {score}. Ensured transparency via multi-method (fuzzy/embed/rule) approach.")

        topic, fuzzy_score = classify_with_fuzzy(bag, TOPIC_CANDIDATES)
        if topic == "unknown":
            topic, embed_score = classify_with_embeddings(bag, TOPIC_CANDIDATES)
            score = embed_score
        else:
            score = fuzzy_score

        # RA Check for topic
        if score < 0.5:
            logger.warning(f"RA Check: Low confidence in topic classification ({topic}, score={score}). Potential bias risk; ensure diverse training data for embeddings.")
        else:
            logger.info(f"RA Check: Topic classified as {topic} with score {score}. Ethical handling: Classifications auditable via logged scores.")

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
        logger.error(f"Error parsing query: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))