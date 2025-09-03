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
from fuzzywuzzy import fuzz
from itertools import groupby

app = FastAPI(title="Citation Extraction Agent")

# Initialize spaCy model with custom rules
nlp = spacy.load("en_core_web_trf")  # Requires spacy-transformers
ruler = nlp.add_pipe("entity_ruler", before="ner")
patterns = [
    # CASE: e.g., "Roe v. Wade"
    {"label": "CASE", "pattern": [
        {"TEXT": {"REGEX": r"^[A-Z][a-zA-Z']+"}}, {"LOWER": "v."}, {"TEXT": {"REGEX": r"^[A-Z][a-zA-Z']+"}}
    ]},
    # REPORTER: e.g., "410 U.S. 113 (1973)"
    {"label": "REPORTER", "pattern": [
        {"LIKE_NUM": True}, {"IS_ALPHA": True, "OP": "?"}, {"LIKE_NUM": True},
        {"TEXT": "(", "OP": "?"}, {"LIKE_NUM": True, "OP": "?"}, {"TEXT": ")", "OP": "?"}
    ]},
    # STATUTE: e.g., "18 U.S.C. § 1341"
    {"label": "STATUTE", "pattern": [
        {"LIKE_NUM": True}, {"IS_ALPHA": True, "OP": "+"}, {"TEXT": "§"}, {"LIKE_NUM": True}
    ]},
    # ACT (stricter): must be Proper Noun + Act, optionally with Section
    {"label": "ACT", "pattern": [
        {"POS": "PROPN", "OP": "+"}, {"LOWER": "act"},
        {"TEXT": ",", "OP": "?"}, {"LOWER": "section", "OP": "?"}, {"LIKE_NUM": True, "OP": "?"}
    ]},
    # CONSTITUTION: e.g., "Amendment XIV, Section 1"
    {"label": "CONSTITUTION", "pattern": [
        {"LOWER": {"IN": ["article", "amendment"]}}, {"LIKE_NUM": True},
        {"TEXT": ",", "OP": "?"}, {"LOWER": "section", "OP": "?"}, {"LIKE_NUM": True, "OP": "?"}
    ]}
]
ruler.add_patterns(patterns)

class CitationRequest(BaseModel):
    case_id: str

class CitationResponse(BaseModel):
    citations: list[str]

async def fetch_case_text(case_id: str) -> str:
    """Fetch case text from CourtListener v4 API with retries."""
    async with httpx.AsyncClient() as client:
        for attempt in range(3):
            try:
                response = await client.get(
                    f"{Config.COURTLISTENER_BASE_URL}opinions/{case_id}/?fields=text,html_lawbox,html_columbia,html,html_with_citations",
                    headers={"Authorization": f"Token {Config.COURTLISTENER_API_KEY}"}
                )
                logger.info(f"Attempt {attempt + 1} - CourtListener API request for case_id {case_id}: URL={response.request.url}, Status={response.status_code}, Response={response.json() if response.status_code == 200 else response.text}")
                response.raise_for_status()
                case_data = response.json()
                case_text = case_data.get("text") or case_data.get("html_lawbox") or case_data.get(
                    "html_columbia") or case_data.get("html") or case_data.get("html_with_citations", "")
                return case_text
            except httpx.HTTPStatusError as e:
                logger.error(f"Attempt {attempt + 1} - CourtListener API error for case_id {case_id}: {str(e)}")
                if attempt == 2:
                    raise HTTPException(status_code=e.response.status_code, detail=str(e))
                await asyncio.sleep(1)
    return ""

def extract_citations_from_text(case_text: str) -> list[str]:
    """Extract citations from case text using regex, spaCy, and Hugging Face NER."""
    import re
    from transformers import pipeline

    # Clean text by removing HTML tags
    case_text = re.sub(r'<[^>]+>', '', case_text)

    # Regex patterns (tightened ACT)
    case_pattern = r"\b[A-Z][a-zA-Z']+(?:\s+[A-Z][a-zA-Z']+)?\s+v\.\s+[A-Z][a-zA-Z']+(?:\s+[A-Z][a-zA-Z']+)?\b(?!\s*(?:said|held|ruled|found))"
    reporter_pattern = r"\b\d+\s+[A-Z][a-zA-Z.]+\s+\d+(?:\s+\(\d{4}\))?\b(?!\s*[a-zA-Z]+)"
    statute_pattern = r"\b\d+\s+[A-Za-z.]+\s+§\s+\d+(?:\.\d+)?\b"
    # Stricter: must start with uppercase + "Act"
    act_pattern = r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+Act\b(?:,\s+Section\s+\d+)?"
    constitution_pattern = r"\b(?:Article|Amendment)\s+[IVXLCDM0-9]+(?:,\s+Section\s+\d+)?\b"

    regex_citations = []
    for pattern in [case_pattern, reporter_pattern, statute_pattern, act_pattern, constitution_pattern]:
        regex_citations.extend(re.findall(pattern, case_text, re.IGNORECASE))
    regex_citations = [cit.strip() for cit in regex_citations if 5 < len(cit) < 50]

    # spaCy pass
    doc = nlp(case_text)
    spacy_citations = []
    for ent in doc.ents:
        if ent.label_ in ("CASE", "REPORTER", "STATUTE", "ACT", "CONSTITUTION"):
            # --- Extra filter: Only keep "ACT" if it's a Proper Noun ---
            if ent.label_ == "ACT" and ent.root.pos_ != "PROPN":
                continue
            # Context filters (same as before)
            if (
                ent.root.dep_ in ("pobj", "dobj", "npadvmod")
                or "(" in ent.sent.text
                or len(ent.sent.text.split()) < 50
                or any(keyword in ent.sent.text.lower() for keyword in ["see ", "in ", "citing ", "at "])
            ):
                spacy_citations.append(ent.text.strip())

    # Combine regex + spaCy
    citations = list(set(regex_citations + spacy_citations))

    # Normalize
    citations = [re.sub(r'[,\.;</i>]+$', '', cit).strip() for cit in citations]
    citations = list(dict.fromkeys(citations))  # preserve order, remove duplicates

    return citations

def validate_with_local_llm(candidates: list[str]) -> list[str]:
    """Validate citations using a local DistilBERT model."""
    try:
        classifier = pipeline(
            "text-classification",
            model="distilbert-base-uncased",
            tokenizer="distilbert-base-uncased",
            framework="pt",
            device=-1  # CPU; use 0 for GPU if available
        )
        valid_citations = []
        for cit in candidates:
            has_legal_pattern = bool(
                re.search(r"\b(v\.|§|\d+\s+(?:U\.S\.|F\.|F\.3d|WL)\s+\d+|\bAct\b|\bArticle\b|\bAmendment\b)", cit, re.IGNORECASE)
            )
            is_short = 5 < len(cit) < 40  # Stricter length
            result = classifier(cit, truncation=True, max_length=128)
            score = result[0]["score"] if result[0]["label"] == "POSITIVE" else 1 - result[0]["score"]
            if (score > 0.8 and has_legal_pattern) or (is_short and has_legal_pattern):  # Stricter score
                valid_citations.append(cit)
            else:
                logger.debug(f"Filtered out invalid citation: {cit} (score={score}, has_legal_pattern={has_legal_pattern})")
        return valid_citations
    except Exception as e:
        logger.error(f"Local LLM error: {str(e)}")
        return candidates  # Fallback: return all if model fails

@app.post("/extract_citations", response_model=CitationResponse)
async def extract_citations(request: CitationRequest, token: str = Depends(verify_token)):
    try:
        logger.info(f"Received case_id: {request.case_id}")
        if not request.case_id:
            logger.error(f"Invalid case_id received: {request.case_id}")
            raise HTTPException(status_code=400, detail="Case ID is required")

        case_text = await fetch_case_text(request.case_id)
        citations = extract_citations_from_text(case_text) if case_text and len(case_text.strip()) >= 10 else []

        if not citations:
            logger.warning(f"No citations found in case text for case_id {request.case_id}")
            citations = []

        logger.info(f"Extracted citations for case_id {request.case_id}: {citations}")
        return CitationResponse(citations=citations)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error extracting citations for case_id {request.case_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))