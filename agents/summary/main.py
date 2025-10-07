from fastapi.middleware.cors import CORSMiddleware
import sys
import asyncio
from common.courtlistener_api import courtlistener_api
from common.models import SummaryRequest, SummaryResponse
from common.config import Config
from common.logging import logger
from common.security import verify_token
import spacy
import re
from transformers import pipeline, T5Tokenizer, T5ForConditionalGeneration
from pydantic import BaseModel
from fastapi import FastAPI, Depends
from bs4 import BeautifulSoup
import warnings
from bs4 import XMLParsedAsHTMLWarning

# Suppress BeautifulSoup warning
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

app = FastAPI(title="Case Summarization Agent")

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

try:
    model_name = "VincentMuriuki/legal-summarizer"
    tokenizer = T5Tokenizer.from_pretrained(
        model_name, token=Config.HUGGINGFACE_API_KEY)
    model = T5ForConditionalGeneration.from_pretrained(
        model_name, token=Config.HUGGINGFACE_API_KEY)
    summarizer = pipeline("summarization", model=model,
                          tokenizer=tokenizer, device=-1)
    nlp = spacy.load("en_core_web_sm")
    logger.info("Summarizer and spaCy loaded")
except Exception as e:
    logger.error(f"Failed to load models: {str(e)}")
    summarizer = nlp = None


def clean_case_text(text: str) -> str:
    if '<' in text:
        soup = BeautifulSoup(text, 'html.parser')
        text = soup.get_text()
    text = re.sub(r"\s+", " ", text).strip()
    return text[:10000]


def chunk_text(text: str, max_chars: int = 800) -> list[str]:
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    current_chunk = []
    current_length = 0
    for sentence in sentences:
        if current_length + len(sentence) > max_chars:
            if current_chunk:
                chunks.append(" ".join(current_chunk))
            current_chunk = [sentence]
            current_length = len(sentence)
        else:
            current_chunk.append(sentence)
            current_length += len(sentence)
    if current_chunk:
        chunks.append(" ".join(current_chunk))
    return [chunk for chunk in chunks if len(chunk) > 30]


async def summarize_chunk(chunk: str, max_length: int = 220, min_length: int = 120) -> str:
    if not summarizer:
        sentences = chunk.split('. ')
        return '. '.join(sentences[:2]) + '.' if len(sentences) > 1 else chunk[:150] + "..."
    try:
        # Prepend "summarize: " as per model card
        chunk = "summarize: " + chunk
        input_length = len(tokenizer.encode(chunk, truncation=True))
        adjusted_max = min(max_length, int(input_length * 0.6))
        adjusted_min = min(min_length, int(adjusted_max * 0.5))
        # Use max_new_tokens instead of max_length to avoid warning
        result = summarizer(chunk, max_new_tokens=adjusted_max,
                            min_length=adjusted_min, do_sample=False)[0]["summary_text"]
        return result
    except Exception as e:
        logger.error(f"Error summarizing: {str(e)}")
        sentences = chunk.split('. ')
        return '. '.join(sentences[:2]) + '.' if len(sentences) > 1 else chunk[:150] + "..."


def extract_case_name(text: str, case_data: dict) -> str:
    for field in ["case_name"]:
        if case_data.get(field):
            return case_data[field]
    match = re.search(
        r"([\w\s&,\.]+)\s+v\.\s+([\w\s&,\.]+)", text, re.IGNORECASE)
    return f"{match.group(1).strip()} v. {match.group(2).strip()}" if match else "Unknown v. Unknown"


def extract_court(text: str, case_data: dict) -> str:
    for field in ["court", "court_citation_string"]:
        if case_data.get(field):
            return case_data[field]
    match = re.search(
        r"(Supreme Court|Court of Appeals|District Court|[\w\s]+Court)", text, re.IGNORECASE)
    return match.group(1).capitalize() if match else "Unknown Court"


def extract_decision(text: str, case_data: dict) -> str:
    for field in ["disposition"]:
        if case_data.get(field):
            return case_data[field]
    text_lower = text.lower()
    for outcome in ["affirmed", "reversed", "remanded", "dismissed", "granted", "denied"]:
        if outcome in text_lower:
            return outcome.capitalize()
    return "Unknown"


async def fetch_case_data(case_id: str) -> dict:
    try:
        case_details = await courtlistener_api.get_case_details(case_id)
        if not case_details:
            return {}
        cluster_data = case_details.get("cluster", {})
        opinions = case_details.get("opinions", [])
        opinion_data = opinions[0] if opinions else {}
        text = opinion_data.get("html_with_citations",
                                "") or opinion_data.get("plain_text", "")
        return {
            "case_name": cluster_data.get("case_name", ""),
            "court": cluster_data.get("court", ""),
            "disposition": cluster_data.get("disposition", ""),
            "docket_number": cluster_data.get("docket_number", ""),
            "text": clean_case_text(text)
        }
    except Exception as e:
        logger.error(f"Error fetching case: {str(e)}")
        return {}


def extract_legal_entities(text: str) -> dict:
    if not nlp:
        return {"persons": [], "organizations": [], "locations": [], "legal_terms": []}
    doc = nlp(text[:5000])
    entities = {"persons": [], "organizations": [],
                "locations": [], "legal_terms": []}
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            entities["persons"].append(ent.text)
        elif ent.label_ == "ORG":
            entities["organizations"].append(ent.text)
        elif ent.label_ == "GPE":
            entities["locations"].append(ent.text)
        elif ent.label_ in ["LAW"]:
            entities["legal_terms"].append(ent.text)
    return entities


@app.post("/summarize", response_model=SummaryResponse)
async def summarize_case(request: SummaryRequest, token: dict = Depends(verify_token)):
    logger.info(f"Received summary request for {request.case_id}")
    try:
        case_data = request.case_data or await fetch_case_data(request.case_id)
        if not case_data:
            return SummaryResponse(summary={"case": "Unknown", "court": "Unknown", "issue": "No data.", "decision": "Unknown", "entities": {}})

        case_name = extract_case_name(case_data.get("text", ""), case_data)
        court_name = extract_court(case_data.get("text", ""), case_data)
        decision = extract_decision(case_data.get("text", ""), case_data)
        case_text = clean_case_text(
            request.case_text or case_data.get("text", ""))

        if not case_text or len(case_text) < 50:
            fallback_summary = f"{case_name} in {court_name} with outcome {decision}."
            return SummaryResponse(summary={"case": case_name, "court": court_name, "issue": fallback_summary, "decision": decision, "entities": {}})

        entities = extract_legal_entities(case_text)
        chunks = chunk_text(case_text)
        summaries = await asyncio.gather(*(summarize_chunk(chunk) for chunk in chunks[:5]))
        final_summary = " ".join(summaries)
        if len(final_summary.split()) > 400:
            final_summary = " ".join(final_summary.split()[:380]) + "..."

        response = SummaryResponse(summary={
            "case": case_name,
            "court": court_name,
            "issue": final_summary,
            "decision": decision,
            "entities": entities
        })
        return response
    except Exception as e:
        logger.error(f"Error summarizing: {str(e)}")
        return SummaryResponse(summary={"case": "Unknown", "court": "Unknown", "issue": "Error.", "decision": "Unknown", "entities": {}})