from fastapi import FastAPI, Depends
import re
import spacy
from common.security import verify_token
from common.logging import logger
from common.config import Config
from common.courtlistener_api import courtlistener_api
from common.models import CitationRequest, CitationResponse
from sentence_transformers import SentenceTransformer
from bs4 import BeautifulSoup
from sentence_transformers.util import cos_sim

app = FastAPI(title="Citation Extraction Agent")

try:
    # Legal-specific NER model
    nlp = spacy.load("opennyaiorg/en_legal_ner_trf")
    embed_model = SentenceTransformer('all-MiniLM-L6-v2')
    logger.info("Models loaded")
except Exception as e:
    logger.error(f"Failed to load models: {str(e)}")
    nlp = embed_model = None


async def fetch_case_text(case_id: str) -> str:
    details = await courtlistener_api.get_case_details(case_id)
    if not details:
        return ""
    opinion = details.get("opinions", [{}])[0]
    html_cit = opinion.get("html_with_citations", "")
    plain = opinion.get("plain_text", "")
    text = html_cit if html_cit else plain
    if '<' in text:
        soup = BeautifulSoup(text, 'html.parser')
        text = soup.get_text()
    text = re.sub(r'\s+', ' ', text).strip()[:10000]
    return text


def extract_citations_from_text(case_text: str) -> list[str]:
    if not case_text:
        return []
    case_pattern = r"\b[A-Z][a-zA-Z']+(?:\s+[A-Z][a-zA-Z']+)?\s+v\.\s+[A-Z][a-zA-Z']+(?:\s+[A-Z][a-zA-Z']+)?\b"
    reporter_pattern = r"\b\d+\s+[A-Z][A-Za-z.]+\s+\d+(?:\s*\(\d{4}\))?\b"
    statute_pattern = r"\b\d+\s+[A-Za-z.]+\s+§\s+\d+(?:\.\d+)?\b"
    regex_cits = list(set(re.findall(case_pattern + '|' +
                      reporter_pattern + '|' + statute_pattern, case_text, re.I)))

    if not nlp:
        return [cit.strip() for cit in regex_cits if 5 < len(cit) < 50]

    doc = nlp(case_text[:10000])
    spacy_cits = [ent.text.strip()
                  for ent in doc.ents if ent.label_ in ["PRECEDENT", "STATUTE", "PROVISION", "CASE_NUMBER"]]

    all_cits = regex_cits + spacy_cits
    if embed_model:
        embeddings = embed_model.encode(all_cits)
        unique_cits = []
        for i, cit in enumerate(all_cits):
            if all(cos_sim(embeddings[i], embed_model.encode([u]))[0][0] <= 0.8 for u in unique_cits):
                unique_cits.append(cit)
        all_cits = unique_cits

    return [cit.strip() for cit in all_cits if 5 < len(cit) < 50]


@app.post("/extract_citations", response_model=CitationResponse)
async def extract_citations(request: CitationRequest, _token: str = Depends(verify_token)):
    logger.info(f"Received citation request for case_id {request.case_id}")
    try:
        case_text = request.case_text or await fetch_case_text(request.case_id)
        if not case_text:
            return CitationResponse(citations=[])

        citations = extract_citations_from_text(case_text)
        logger.info(f"Extracted {len(citations)} citations")
        return CitationResponse(citations=citations)
    except Exception as e:
        logger.error(f"Error extracting citations: {str(e)}")
        return CitationResponse(citations=[])