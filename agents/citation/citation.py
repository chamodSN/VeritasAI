from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
import re
import httpx
import asyncio
import spacy
from spacy.language import Language
from spacy.tokens import Doc
from common.security import verify_token
from common.logging import logger
from common.config import Config

app = FastAPI(title="Citation Extraction Agent")

# Initialize spaCy model with custom rules
nlp = spacy.load("en_core_web_sm")
ruler = nlp.add_pipe("entity_ruler", before="ner")
patterns = [
    {"label": "CASE", "pattern": [{"TEXT": {
        "REGEX": r"^[A-Z][a-zA-Z](?:\s+[A-Z][a-zA-Z])\s+v\.\s+[A-Z][a-zA-Z](?:\s+[A-Z][a-zA-Z])$"}}]},
    {"label": "REPORTER", "pattern": [
        {"TEXT": {"REGEX": r"^\d+\s+[A-Z][a-zA-Z]*\s+\d+(?:\s+\(\d{4}\))?$"}}]},
    {"label": "STATUTE", "pattern": [
        {"TEXT": {"REGEX": r"^\d+\s+[A-Za-z]+\s+§\s+\d+(?:\.\d+)?$"}}]},
    {"label": "ACT", "pattern": [
        {"TEXT": {"REGEX": r"^[A-Za-z\s]+Act(?:,\s+Section\s+\d+)?$"}}]},
    {"label": "CONSTITUTION", "pattern": [
        {"TEXT": {"REGEX": r"^(?:Article|Amendment)\s+[A-Z0-9]+,\s+Section\s+\d+$"}}]}
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
                    headers={
                        "Authorization": f"Token {Config.COURTLISTENER_API_KEY}"}
                )
                logger.info(f"Attempt {attempt + 1} - CourtListener API request for case_id {case_id}: URL={response.request.url}, Status={response.status_code}, Response={response.json() if response.status_code == 200 else response.text}")
                response.raise_for_status()
                case_data = response.json()
                case_text = case_data.get("text") or case_data.get("html_lawbox") or case_data.get(
                    "html_columbia") or case_data.get("html") or case_data.get("html_with_citations", "")
                return case_text
            except httpx.HTTPStatusError as e:
                logger.error(
                    f"Attempt {attempt + 1} - CourtListener API error for case_id {case_id}: {str(e)}")
                if attempt == 2:
                    raise HTTPException(
                        status_code=e.response.status_code, detail=str(e))
                await asyncio.sleep(1)
    return ""


def extract_citations_from_text(case_text: str) -> list[str]:
    """Extract citations from case text using regex and spaCy."""
    # Clean text by removing HTML tags
    case_text = re.sub(r'<[^>]+>', '', case_text)

    # Enhanced regex for legal citations
    citation_pattern = r"\b(?:[A-Z][a-zA-Z](?:\s+[A-Z][a-zA-Z])\s+v\.\s+[A-Z][a-zA-Z](?:\s+[A-Z][a-zA-Z])|\d+\s+[A-Z][a-zA-Z]*\s+\d+(?:\s+\(\d{4}\))?|\d+\s+[A-Za-z]+\s+§\s+\d+(?:\.\d+)?|[A-Za-z\s]+Act(?:,\s+Section\s+\d+)?|(?:Article|Amendment)\s+[A-Z0-9]+,\s+Section\s+\d+)\b"
    regex_citations = re.findall(citation_pattern, case_text, re.IGNORECASE)

    # Use spaCy with custom rules
    doc = nlp(case_text)
    spacy_citations = [ent.text.strip() for ent in doc.ents if ent.label_ in (
        "CASE", "REPORTER", "STATUTE", "ACT", "CONSTITUTION")]

    # Combine and deduplicate
    citations = list(set(regex_citations + spacy_citations))

    # Filter invalid citations
    blocklist = ["this Memorandum Opinion", "First Amended Complaint",
                 "Civil Action No", "40 to 50", "another Declaration"]
    citations = [cit for cit in citations if not any(
        blocked in cit for blocked in blocklist) and len(cit) > 5 and not cit.isdigit()]

    # Normalize citations (remove trailing punctuation, HTML artifacts)
    citations = [re.sub(r'[,\.;</i>]+$', '', cit).strip() for cit in citations]
    # Preserve order, remove duplicates
    citations = list(dict.fromkeys(citations))

    logger.debug(f"Extracted citations from text: {citations}")
    return citations


@app.post("/extract_citations", response_model=CitationResponse)
async def extract_citations(request: CitationRequest, token: str = Depends(verify_token)):
    try:
        logger.info(f"Received case_id: {request.case_id}")
        if not request.case_id:
            logger.error(f"Invalid case_id received: {request.case_id}")
            raise HTTPException(status_code=400, detail="Case ID is required")

        # Fetch case text from CourtListener
        case_text = await fetch_case_text(request.case_id)

        # Extract citations from case text
        citations = extract_citations_from_text(
            case_text) if case_text and len(case_text.strip()) >= 10 else []

        if not citations:
            logger.warning(
                f"No citations found in case text for case_id {request.case_id}")
            citations = []

        logger.info(
            f"Extracted citations for case_id {request.case_id}: {citations}")
        return CitationResponse(citations=citations)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(
            f"Error extracting citations for case_id {request.case_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))