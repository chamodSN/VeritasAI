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
from nltk.corpus import wordnet
import re
from bs4 import BeautifulSoup
from datetime import datetime
import warnings
from bs4 import XMLParsedAsHTMLWarning
import spacy  # Add for better phrase extraction

# Suppress warnings
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

app = FastAPI(title="Precedent Finding Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

embed_model = SentenceTransformer('all-MiniLM-L6-v2')
try:
    nlp_phrases = spacy.load("en_core_web_sm")  # For noun chunks
except:
    nlp_phrases = None


class PrecedentRequestExtended(PrecedentRequest):
    max_results: int = 5
    similarity_threshold: float = 0.3


def clean_case_text(text: str) -> str:
    if '<' in text:
        soup = BeautifulSoup(text, 'html.parser')
        text = soup.get_text()
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:2000] if len(text) > 2000 else text


def expand_key_phrases(text: str) -> str:
    cleaned = clean_case_text(text).lower()

    # Use spaCy for legal-relevant phrases (noun chunks) if available
    phrases = []
    if nlp_phrases:
        doc = nlp_phrases(cleaned[:2000])  # Limit for speed
        phrases = [chunk.text for chunk in doc.noun_chunks if len(
            chunk.text.split()) <= 3]  # Short legal phrases
    else:
        # Fallback: Extract common legal bigrams/unigrams (filter noise)
        words = re.findall(r'\b[a-z]{3,}\b', cleaned)  # 3+ letters
        phrases = words[:8] + [' '.join(words[i:i+2])
                               for i in range(min(6, len(words)-1))]
        # Filter junk
        phrases = [p for p in set(phrases) if 'or' not in p and len(p) > 3]

    phrases = phrases[:8]  # Limit
    if not phrases:
        return cleaned[:100]  # Fallback to text snippet

    # Expand with filtered synonyms (skip duplicates, short/irrelevant)
    expanded_phrases = []
    for phrase in phrases:
        words_in_phrase = phrase.split()
        syn_variants = []
        has_good_syn = False
        for word in words_in_phrase:
            synsets = wordnet.synsets(word)
            if synsets:
                lemma = synsets[0].lemmas()[0].name().replace('_', ' ')
                # Filter bad ones
                if lemma != word and len(lemma) > 2 and lemma not in ['joule', 'unit', 'etc.']:
                    syn_variants.append(lemma)
                    has_good_syn = True
            if not syn_variants:  # Keep original if no good syn
                syn_variants = [word]
        if has_good_syn and len(syn_variants) == len(words_in_phrase):
            expanded_phrases.append(f"({phrase} OR {' '.join(syn_variants)})")
        else:
            expanded_phrases.append(phrase)

    query = " ".join(expanded_phrases)
    logger.info(f"Generated query: {query[:100]}...")
    # Fallback if poor
    return query if len(expanded_phrases) >= 2 else ' '.join(phrases)


async def find_similar_cases(case_text: str, case_id: str, input_date: str = "", max_results: int = 5, threshold: float = 0.3) -> List[Dict[str, Any]]:
    if not case_text or len(case_text) < 50:
        logger.warning("Insufficient input text for similarity search")
        return []

    cleaned = clean_case_text(case_text)
    query = expand_key_phrases(cleaned)

    # Try search; fallback if error
    search_results = await courtlistener_api.search_cases(query=query, page_size=20)
    if not search_results.get("results"):
        logger.warning("Search failed; trying simpler query")
        simple_query = ' '.join(re.findall(
            r'\b[a-z]{4,}\b', cleaned.lower())[:10])  # Top words
        search_results = await courtlistener_api.search_cases(query=simple_query, page_size=20)

    candidates = [c for c in search_results.get(
        "results", []) if str(c.get("cluster_id")) != case_id]
    logger.info(f"Found {len(candidates)} initial candidates")

    if not candidates or not embed_model:
        return candidates[:max_results]

    try:
        case_emb = embed_model.encode([cleaned])[0]
    except Exception as emb_err:
        logger.error(f"Failed to embed input text: {emb_err}")
        return []

    similar = []
    cutoff_date = datetime.strptime(
        input_date[:10], '%Y-%m-%d') if input_date else datetime.now()

    for c in candidates:
        c_text = clean_case_text(
            c.get('html_with_citations', '') or c.get('plain_text', ''))
        if len(c_text) < 50:  # Skip too short
            continue

        try:
            c_emb = embed_model.encode([c_text])[0]
            sim = np.dot(case_emb, c_emb) / \
                (np.linalg.norm(case_emb) * np.linalg.norm(c_emb))
            sim = float(sim)  # Ensure Python float
        except Exception as emb_err:
            logger.warning(
                f"Embedding error for candidate {c.get('cluster_id')}: {emb_err}")
            continue

        # Date filter
        date_filed_str = c.get("date_filed", "")
        try:
            case_date = datetime.strptime(
                date_filed_str[:10], '%Y-%m-%d') if date_filed_str else cutoff_date
            if case_date >= cutoff_date:
                continue
        except ValueError:
            continue

        if sim >= threshold:
            c["similarity_score"] = sim
            similar.append(c)

    similar.sort(key=lambda x: x["similarity_score"], reverse=True)
    logger.info(f"After filtering, {len(similar)} similar cases")
    return similar[:max_results]


@app.post("/find_precedents", response_model=PrecedentResponse)
async def find_precedents(request: PrecedentRequestExtended, token: dict = Depends(verify_token)):
    logger.info(f"Received precedent request for {request.case_id}")
    try:
        if request.max_results > Config.MAX_RESULTS_PER_QUERY:
            request.max_results = Config.MAX_RESULTS_PER_QUERY

        case_text = request.case_text or await courtlistener_api.get_case_text(request.case_id)
        if not case_text:
            logger.warning("No case text available")
            return PrecedentResponse(related_cases=[])

        case_details = await courtlistener_api.get_case_details(request.case_id)
        input_date = case_details.get("cluster", {}).get("date_filed", "")

        similar_cases = await find_similar_cases(case_text, request.case_id, input_date, request.max_results, request.similarity_threshold)

        formatted_cases = [
            {
                "id": str(case.get("cluster_id", "")),
                "title": case.get("case_name", "Unknown"),
                "court": case.get("court", "Unknown"),
                "date": str(case.get("date_filed", "")),
                # Safe float
                "similarity_score": float(case.get("similarity_score", 0.0))
            }
            for case in similar_cases
        ]
        logger.info(f"Found {len(formatted_cases)} precedents")
        return PrecedentResponse(related_cases=formatted_cases)
    except Exception as e:
        logger.error(f"Error finding precedents: {str(e)}")
        return PrecedentResponse(related_cases=[])