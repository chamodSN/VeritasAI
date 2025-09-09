from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
import re
import httpx
import asyncio
import spacy
from common.security import verify_token
from common.logging import logger
from common.config import Config
from transformers import pipeline
from fastapi.middleware.cors import CORSMiddleware
from common.models import CitationRequest, CitationResponse

app = FastAPI(title="Citation Extraction Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

nlp = spacy.load("en_core_web_trf")
ruler = nlp.add_pipe("entity_ruler", before="ner")
patterns = [
    {"label": "CASE", "pattern": [
        {"TEXT": {"REGEX": r"^[A-Z][a-zA-Z']+"}}, {"LOWER": "v."}, {"TEXT": {"REGEX": r"^[A-Z][a-zA-Z']+"}}]},
    {"label": "REPORTER", "pattern": [
        {"LIKE_NUM": True}, {"IS_ALPHA": True, "OP": "?"}, {"LIKE_NUM": True},
        {"TEXT": "(", "OP": "?"}, {"LIKE_NUM": True,
                                   "OP": "?"}, {"TEXT": ")", "OP": "?"}
    ]},
    {"label": "STATUTE", "pattern": [
        {"LIKE_NUM": True}, {"IS_ALPHA": True, "OP": "+"}, {"TEXT": "§"}, {"LIKE_NUM": True}]},
    {"label": "ACT", "pattern": [
        {"POS": "PROPN", "OP": "+"}, {"LOWER": "act"},
        {"TEXT": ",", "OP": "?"}, {"LOWER": "section", "OP": "?"}, {"LIKE_NUM": True, "OP": "?"}]},
    {"label": "CONSTITUTION", "pattern": [
        {"LOWER": {"IN": ["article", "amendment"]}}, {"LIKE_NUM": True},
        {"TEXT": ",", "OP": "?"}, {"LOWER": "section", "OP": "?"}, {"LIKE_NUM": True, "OP": "?"}]}
]
ruler.add_patterns(patterns)

try:
    classifier = pipeline("zero-shot-classification",
                          model="facebook/bart-large-mnli")
    logger.info("Zero-shot classifier loaded successfully")
except Exception as e:
    logger.error(f"Failed to load zero-shot classifier: {str(e)}")
    classifier = None


async def fetch_case_data(case_id: str, client: httpx.AsyncClient) -> dict:
    try:
        response = await client.get(
            f"{Config.COURTLISTENER_BASE_URL}opinions/{case_id}/?fields=plain_text,html_lawbox,html_columbia,html,html_with_citations",
            headers={"Authorization": f"Token {Config.COURTLISTENER_API_KEY}"}
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(
            f"CourtListener API error for case_id {case_id}: {str(e)}")
        return {}
    except Exception as e:
        logger.error(
            f"Error fetching case data for case_id {case_id}: {str(e)}")
        return {}


def extract_citations_from_text(case_text: str) -> list[str]:
    case_text = re.sub(r'<[^>]+>', '', case_text)
    case_pattern = r"\b[A-Z][a-zA-Z']+(?:\s+[A-Z][a-zA-Z']+)?\s+v\.\s+[A-Z][a-zA-Z']+(?:\s+[A-Z][a-zA-Z']+)?\b(?!\s*(?:said|held|ruled|found))"
    reporter_pattern = r"\b\d+\s+[A-Z][a-zA-Z.]+\s+\d+(?:\s+\(\d{4}\))?\b(?!\s*[a-zA-Z]+)"
    statute_pattern = r"\b\d+\s+[A-Za-z.]+\s+§\s+\d+(?:\.\d+)?\b"
    act_pattern = r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+Act\b(?:,\s+Section\s+\d+)?"
    constitution_pattern = r"\b(?:Article|Amendment)\s+[IVXLCDM0-9]+(?:,\s+Section\s+\d+)?\b"

    regex_citations = []
    for pattern in [case_pattern, reporter_pattern, statute_pattern, act_pattern, constitution_pattern]:
        regex_citations.extend(re.findall(pattern, case_text, re.IGNORECASE))
    regex_citations = [cit.strip()
                       for cit in regex_citations if 5 < len(cit) < 50]

    doc = nlp(case_text)
    spacy_citations = []
    for ent in doc.ents:
        if ent.label_ in ("CASE", "REPORTER", "STATUTE", "ACT", "CONSTITUTION"):
            if ent.label_ == "ACT" and ent.root.pos_ != "PROPN":
                continue
            if (
                ent.root.dep_ in ("pobj", "dobj", "npadvmod")
                or "(" in ent.sent.text
                or len(ent.sent.text.split()) < 50
                or any(keyword in ent.sent.text.lower() for keyword in ["see ", "in ", "citing ", "at "])
            ):
                spacy_citations.append(ent.text.strip())

    citations = list(set(regex_citations + spacy_citations))
    citations = [re.sub(r'[,\.;</i>]+$', '', cit).strip() for cit in citations]
    citations = list(dict.fromkeys(citations))
    return citations


def validate_with_local_llm(candidates: list[str]) -> list[str]:
    if not classifier:
        logger.warning(
            "No LLM classifier available, returning unvalidated citations")
        return candidates
    try:
        valid_citations = []
        for cit in candidates:
            result = classifier(cit, candidate_labels=[
                                "legal citation", "non-citation"])
            if result['labels'][0] == "legal citation" and result['scores'][0] > 0.7:
                valid_citations.append(cit)
        return valid_citations
    except Exception as e:
        logger.error(f"Local LLM error: {str(e)}")
        return candidates


@app.post("/extract_citations", response_model=CitationResponse)
async def extract_citations(request: CitationRequest, token: dict = Depends(verify_token)):
    try:
        logger.info(f"Received case_id: {request.case_id}")
        if not request.case_id:
            logger.error(f"Invalid case_id received: {request.case_id}")
            raise HTTPException(status_code=400, detail="Case ID is required")

        async with httpx.AsyncClient(timeout=30) as client:
            case_data = request.case_data or await fetch_case_data(request.case_id, client)
        case_text = (
            case_data.get("plain_text") or
            case_data.get("html_lawbox") or
            case_data.get("html_columbia") or
            case_data.get("html") or
            case_data.get("html_with_citations", "")
        )

        citations = extract_citations_from_text(
            case_text) if case_text and len(case_text.strip()) >= 50 else []
        if not citations:
            logger.warning(
                f"No citations found in case text for case_id {request.case_id}")
            citations = []

        citations = validate_with_local_llm(citations)
        logger.info(
            f"Extracted citations for case_id {request.case_id}: {citations}")
        return CitationResponse(citations=citations)
    except httpx.HTTPStatusError as e:
        logger.error(
            f"CourtListener API error for case_id {request.case_id}: {str(e)}")
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        logger.error(
            f"Error extracting citations for case_id {request.case_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))