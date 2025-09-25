from fastapi import FastAPI, Depends
import re
import spacy
from common.security import verify_token
from common.logging import logger
from common.config import Config
from common.courtlistener_api import courtlistener_api
from common.models import CitationRequest, CitationResponse

app = FastAPI(title="Citation Extraction Agent")

try:
    nlp = spacy.load("en_core_web_sm")
    ruler = nlp.add_pipe("entity_ruler", before="ner")
    patterns = [
        {"label": "CASE", "pattern": [{"TEXT": {"REGEX": r"^[A-Z][a-zA-Z']+"}}, {
            "LOWER": "v."}, {"TEXT": {"REGEX": r"^[A-Z][a-zA-Z']+"}}]},
        {"label": "REPORTER", "pattern": [{"LIKE_NUM": True}, {"IS_ALPHA": True}, {"LIKE_NUM": True}, {
            "TEXT": "(", "OP": "?"}, {"LIKE_NUM": True, "OP": "?"}, {"TEXT": ")", "OP": "?"}]},
        {"label": "STATUTE", "pattern": [{"LIKE_NUM": True}, {
            "IS_ALPHA": True, "OP": "+"}, {"TEXT": "§"}, {"LIKE_NUM": True}]}
    ]
    ruler.add_patterns(patterns)
    logger.info("Spacy NLP model loaded with entity ruler")
except Exception as e:
    logger.error(f"Failed to load spacy model: {str(e)}")
    nlp = None


async def fetch_case_text(case_id: str) -> str:
    try:
        text = await courtlistener_api.get_case_text(case_id)
        logger.info(f"Fetched case text for {case_id}: {text[:100]}...")
        return text
    except Exception as e:
        logger.error(f"Error fetching case text for {case_id}: {str(e)}")
        return ""


def extract_citations_from_text(case_text: str) -> list[str]:
    if not case_text:
        logger.warning("Empty case text provided")
        return []
    case_text = re.sub(r'<[^>]+>', '', case_text)
    case_pattern = r"\b[A-Z][a-zA-Z']+(?:\s+[A-Z][a-zA-Z']+)?\s+v\.\s+[A-Z][a-zA-Z']+(?:\s+[A-Z][a-zA-Z']+)?\b"
    reporter_pattern = r"\b\d+\s+[A-Z][A-Za-z.]+\s+\d+(?:\s*\(\d{4}\))?\b"
    statute_pattern = r"\b\d+\s+[A-Za-z.]+\s+§\s+\d+(?:\.\d+)?\b"

    regex_citations = []
    for pattern in [case_pattern, reporter_pattern, statute_pattern]:
        regex_citations.extend(re.findall(pattern, case_text, re.IGNORECASE))

    if not nlp:
        logger.warning("Spacy NLP not loaded, using regex only")
        citations = list(set(regex_citations))
        return [cit.strip() for cit in citations if 5 < len(cit) < 50]

    try:
        doc = nlp(case_text[:10000])  # Limit for performance
        spacy_citations = [ent.text.strip() for ent in doc.ents if ent.label_ in (
            "CASE", "REPORTER", "STATUTE")]
        citations = list(set(regex_citations + spacy_citations))
        citations = [cit.strip() for cit in citations if 5 < len(cit) < 50]
        return citations
    except Exception as e:
        logger.error(f"Error extracting citations with spacy: {str(e)}")
        citations = list(set(regex_citations))
        return [cit.strip() for cit in citations if 5 < len(cit) < 50]


@app.post("/extract_citations", response_model=CitationResponse)
async def extract_citations(request: CitationRequest, _token: str = Depends(verify_token)):
    logger.info(f"Received citation request for case_id {request.case_id}")
    try:
        if not request.case_id:
            logger.warning(f"Invalid case_id {request.case_id}")
            return CitationResponse(citations=[])

        case_text = request.case_text or await fetch_case_text(request.case_id)
        if not case_text or len(case_text.strip()) < 10:
            logger.warning(f"Insufficient text for case_id {request.case_id}")
            return CitationResponse(citations=[])

        citations = extract_citations_from_text(case_text)
        if not citations:
            logger.warning(f"No citations found for case_id {request.case_id}")
        else:
            citation_lengths = [len(cit) for cit in citations]
            avg_length = sum(citation_lengths) / \
                len(citation_lengths) if citation_lengths else 0
            if avg_length < 10 or avg_length > 50:
                logger.warning(
                    f"RA Check: Abnormal citation lengths (avg: {avg_length}) for case_id {request.case_id}")

        logger.info(
            f"Extracted {len(citations)} citations for case_id {request.case_id}")
        return CitationResponse(citations=citations)

    except Exception as e:
        logger.error(
            f"Error extracting citations for case_id {request.case_id}: {str(e)}")
        return CitationResponse(citations=[])
