from .ir import router as ir_router
from fastapi.middleware.cors import CORSMiddleware
from common.config import Config
from common.models import SearchRequest
from common.logging import logger
from common.security import verify_token
from common.responsible_ai import responsible_ai
import numpy as np
from sentence_transformers import SentenceTransformer
from rapidfuzz import process
import httpx
import spacy
from typing import List, Tuple, Set
from pydantic import BaseModel
from fastapi import FastAPI, Depends, HTTPException
from .utils import parse_dates_smart
from nltk.corpus import wordnet
import nltk
import asyncio
import xml.etree.ElementTree as ET  # For parsing SPARQL XML
nltk.download('wordnet', quiet=True)

# -----------------------------------------------------------
# FASTAPI APP SETUP
# -----------------------------------------------------------
app = FastAPI(title="Query Understanding Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ir_router, tags=["search"])

# -----------------------------------------------------------
# MODEL INITIALIZATION
# -----------------------------------------------------------
nlp = spacy.load("en_core_web_sm")
embed_model = SentenceTransformer('all-MiniLM-L6-v2')

# Maximum characters for topic/case_type labels
MAX_LABEL_LENGTH = 30

# Wikidata SPARQL endpoint
WIKIDATA_SPARQL_URL = "https://query.wikidata.org/sparql"

# -----------------------------------------------------------
# FETCH LEGAL TERMS DYNAMICALLY
# -----------------------------------------------------------


async def fetch_wikidata_legal_terms() -> Tuple[Set[str], Set[str]]:
    """Fetch dynamic case types and topics from Wikidata using SPARQL."""
    try:
        # SPARQL query for case types: Subclasses of "legal case" (Q2334719) or "type of lawsuit" (Q1762010)
        case_type_sparql = """
        SELECT DISTINCT ?itemLabel WHERE {
          ?item wdt:P279* wd:Q2334719 .  # Subclasses of legal case
          SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
        } LIMIT 100
        """

        # SPARQL query for topics: Subclasses of "branch of law" (Q164888) or "legal concept" (Q2135465)
        topic_sparql = """
        SELECT DISTINCT ?itemLabel WHERE {
          ?item wdt:P279* wd:Q164888 .  # Subclasses of branch of law
          SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
        } LIMIT 100
        """

        async def query_sparql(sparql: str) -> Set[str]:
            async with httpx.AsyncClient(timeout=15) as client:
                params = {"query": sparql, "format": "xml"}
                res = await client.get(WIKIDATA_SPARQL_URL, params=params)
                res.raise_for_status()
                root = ET.fromstring(res.content)
                terms = set()
                for binding in root.findall(".//{http://www.w3.org/2005/sparql-results#}binding[@name='itemLabel']/{http://www.w3.org/2005/sparql-results#}literal"):
                    label = binding.text.strip()
                    if len(label) <= MAX_LABEL_LENGTH and label.lower() not in terms:
                        terms.add(label.lower())
                return terms

        case_types = await query_sparql(case_type_sparql)
        topics = await query_sparql(topic_sparql)

        # Merge with CourtListener/Open Legal Data if needed (e.g., via additional queries or static)
        # For now, Wikidata is primary; add if more sources available

        if not case_types or not topics:
            logger.warning(
                "Wikidata fetch returned empty; using minimal fallback")
            case_types = {"criminal law", "civil law",
                          "tax law", "contract law"}
            topics = {"human rights", "environmental law",
                      "intellectual property", "corporate law"}

        return case_types, topics

    except Exception as e:
        logger.error(f"Failed to fetch legal terms from Wikidata: {str(e)}")
        return set(), set()  # Empty to force "unknown" if fail

# Global sets for classification
LEGAL_CASE_TYPES: Set[str] = set()
LEGAL_TOPICS: Set[str] = set()


@app.on_event("startup")
async def load_legal_terms():
    """Load legal terms asynchronously at FastAPI startup."""
    global LEGAL_CASE_TYPES, LEGAL_TOPICS
    LEGAL_CASE_TYPES, LEGAL_TOPICS = await fetch_wikidata_legal_terms()
    logger.info(
        f"✅ Legal terms loaded: {len(LEGAL_CASE_TYPES)} case types, {len(LEGAL_TOPICS)} topics")

# -----------------------------------------------------------
# CLASSIFICATION FUNCTIONS
# -----------------------------------------------------------


def classify_with_embeddings(text: str, candidates: Set[str], min_score: float = 0.25) -> Tuple[str, float]:
    """Return best matching candidate using embeddings, respecting MAX_LABEL_LENGTH."""
    if not text or not candidates:
        return "unknown", 0.0
    q = embed_model.encode([text])[0]
    cands_list = [c for c in candidates if len(
        c) <= MAX_LABEL_LENGTH]  # enforce length
    if not cands_list:
        return "unknown", 0.0
    cands_embeddings = embed_model.encode(cands_list)
    sims = [np.dot(q, c) / (np.linalg.norm(q) * np.linalg.norm(c))
            for c in cands_embeddings]
    best_idx = int(np.argmax(sims))
    best_score = sims[best_idx]
    return cands_list[best_idx] if best_score >= min_score else "unknown", best_score


def classify_with_fuzzy(text: str, candidates: Set[str], min_score: int = 70) -> Tuple[str, float]:
    """Return best matching candidate using fuzzy matching, respecting MAX_LABEL_LENGTH."""
    if not text or not candidates:
        return "unknown", 0.0
    cands_list = [c for c in candidates if len(c) <= MAX_LABEL_LENGTH]
    if not cands_list:
        return "unknown", 0.0
    result = process.extractOne(text, cands_list, score_cutoff=min_score)
    return (result[0], result[1] / 100.0) if result else ("unknown", 0.0)


def expand_query_with_synonyms(text: str) -> str:
    """Expand query terms with up to 2 synonyms from WordNet."""
    words = text.split()
    expanded = []
    for word in words:
        synonyms = set([lemma.name() for synset in wordnet.synsets(word)
                       for lemma in synset.lemmas()])
        if synonyms:
            expanded.append(f"({word} OR {' OR '.join(list(synonyms)[:2])})")
        else:
            expanded.append(word)
    return " ".join(expanded)

# -----------------------------------------------------------
# MAIN ENDPOINT
# -----------------------------------------------------------


@app.post("/parse_query", response_model=SearchRequest, tags=["parse"])
async def parse_query(request: SearchRequest, token: dict = Depends(verify_token)):
    try:
        if len(request.raw_query or "") > Config.MAX_QUERY_LENGTH:
            raise HTTPException(
                status_code=400, detail=f"Query too long. Max: {Config.MAX_QUERY_LENGTH} chars")

        q = (request.raw_query or "").lower()
        doc = nlp(q)
        date_from, date_to = parse_dates_smart(q)

        legal_entities = [ent.text.lower() for ent in doc.ents if ent.label_ in [
            "ORG", "PERSON", "GPE", "LAW"]]
        bag = " ".join(legal_entities + [chunk.text.lower()
                       for chunk in doc.noun_chunks])

        # Classify case type dynamically
        case_type, score = classify_with_fuzzy(bag, LEGAL_CASE_TYPES)
        if case_type == "unknown":
            case_type, score = classify_with_embeddings(bag, LEGAL_CASE_TYPES)

        # Classify topic dynamically
        topic, topic_score = classify_with_fuzzy(bag, LEGAL_TOPICS)
        if topic == "unknown":
            topic, topic_score = classify_with_embeddings(bag, LEGAL_TOPICS)

        expanded_query = expand_query_with_synonyms(q)

        if Config.ENABLE_BIAS_DETECTION:
            fairness_check = await responsible_ai.check_query_fairness(q)
            if not fairness_check.get("is_fair", True):
                logger.warning(
                    f"Query bias: {fairness_check.get('warnings', [])}")

        resp = SearchRequest(
            case_type=case_type,
            topic=topic,
            date_from=date_from or request.date_from,
            date_to=date_to or request.date_to,
            raw_query=expanded_query,
            court=request.court
        )
        logger.info(f"Parsed query: {q} -> {resp.dict()}")
        return resp
    except Exception as e:
        logger.error(f"Error parsing query: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
