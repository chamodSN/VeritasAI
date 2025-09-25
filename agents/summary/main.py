from fastapi.middleware.cors import CORSMiddleware
import sys
import asyncio
from common.courtlistener_api import courtlistener_api
from common.models import SummaryRequest, SummaryResponse
from common.config import Config
from common.logging import logger
from common.security import verify_token
import spacy
import asyncio
import re
import httpx
from transformers import pipeline, AutoTokenizer
from pydantic import BaseModel
from fastapi import FastAPI, Depends

app = FastAPI(title="Case Summarization Agent")

# Windows-specific workaround to reduce noisy ConnectionResetError logs
if sys.platform.startswith("win"):
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        pass

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

try:
    model_name = "facebook/bart-large-cnn"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    summarizer = pipeline(
        "summarization",
        model=model_name,
        tokenizer=tokenizer,
        device=-1,
        framework="pt"
    )
    nlp = spacy.load("en_core_web_sm")
    logger.info("Summarization and NER models loaded")
except Exception as e:
    logger.error(f"Failed to load models: {str(e)}")
    summarizer = None
    nlp = None


def clean_case_text(text: str) -> str:
    text = re.sub(r"<.*?>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"[^\x00-\x7F]+", "", text)
    return text[:10000]  # Limit for performance


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
        input_length = len(tokenizer.encode(chunk, truncation=True))
        # Dynamic sizing: aim for ~50-65% of input tokens, with safe bounds
        target_max = max(50, int(input_length * 0.6))
        adjusted_max_length = min(max_length, target_max, max(10, input_length - 5))
        adjusted_max_length = max(adjusted_max_length, 40)
        adjusted_min_length = min(
            max(30, int(adjusted_max_length * 0.5)),
            max(10, adjusted_max_length - 20)
        )
        if adjusted_min_length >= adjusted_max_length:
            adjusted_min_length = max(20, adjusted_max_length // 2)
        result = summarizer(chunk, max_length=adjusted_max_length,
                            min_length=min(adjusted_max_length - 40, adjusted_min_length), do_sample=False)[0]["summary_text"]
        return result
    except Exception as e:
        logger.error(f"Error summarizing chunk: {str(e)}")
        sentences = chunk.split('. ')
        return '. '.join(sentences[:2]) + '.' if len(sentences) > 1 else chunk[:150] + "..."


def extract_case_name(text: str, case_data: dict) -> str:
    for field in ["caseName", "case_name", "caseNameFull", "caseNameShort", "title"]:
        if case_data.get(field):
            return case_data[field]
    match = re.search(
        r"([\w\s&,\.]+)\s+v\.\s+([\w\s&,\.]+)", text, re.IGNORECASE)
    return f"{match.group(1).strip()} v. {match.group(2).strip()}" if match else "Unknown vs Unknown"


def extract_court(text: str, case_data: dict) -> str:
    for field in ["court_citation_string", "court_name", "court"]:
        if case_data.get(field):
            return case_data[field]
    # Broader regex to capture court names
    match = re.search(
        r"(Supreme Court|Court of Appeals|Circuit Court|District Court|Court of [\w\s]+|[\w\s]+Court)", text, re.IGNORECASE)
    return match.group(1).capitalize() if match else "Unknown Court"


def extract_decision(text: str, case_data: dict) -> str:
    for field in ["disposition", "status", "decision"]:
        if case_data.get(field):
            return case_data[field]
    # Search entire text for decision keywords
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
        return {
            "caseName": cluster_data.get("case_name", opinion_data.get("caseName", "")),
            "court_citation_string": cluster_data.get("court_name", opinion_data.get("court_citation_string", "")),
            "disposition": cluster_data.get("disposition", opinion_data.get("disposition", "")),
            "docketNumber": cluster_data.get("docket_number", opinion_data.get("docketNumber", "")),
            "text": opinion_data.get("text", "") or opinion_data.get("html_lawbox", "") or opinion_data.get("html", "")
        }
    except Exception as e:
        logger.error(f"Error fetching case data for {case_id}: {str(e)}")
        return {}


def extract_legal_entities(text: str) -> dict:
    if not nlp:
        return {"persons": [], "organizations": [], "locations": [], "legal_terms": []}
    doc = nlp(text[:5000])  # Limit for performance
    entities = {"persons": [], "organizations": [],
                "locations": [], "legal_terms": []}
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            entities["persons"].append(ent.text)
        elif ent.label_ == "ORG":
            entities["organizations"].append(ent.text)
        elif ent.label_ == "GPE":
            entities["locations"].append(ent.text)
        elif ent.label_ in ["LAW", "EVENT"]:
            entities["legal_terms"].append(ent.text)
    return entities


@app.post("/summarize", response_model=SummaryResponse)
async def summarize_case(request: SummaryRequest, token: dict = Depends(verify_token)):
    logger.info(f"Received summary request for case_id {request.case_id}")
    try:
        if not request.case_id or not request.case_id.isdigit():
            logger.warning(f"Invalid case_id {request.case_id}")
            return SummaryResponse(summary={
                "case": "Unknown",
                "court": "Unknown",
                "issue": "Invalid case ID provided.",
                "decision": "Unknown",
                "entities": {"persons": [], "organizations": [], "locations": [], "legal_terms": []}
            })

        case_data = request.case_data or await fetch_case_data(request.case_id)
        if not case_data:
            logger.warning(f"No case data for case_id {request.case_id}")
            return SummaryResponse(summary={
                "case": "Unknown",
                "court": "Unknown",
                "issue": "No case data found.",
                "decision": "Unknown",
                "entities": {"persons": [], "organizations": [], "locations": [], "legal_terms": []}
            })

        case_name = extract_case_name("", case_data)
        court_name = extract_court(case_data.get("text", ""), case_data)
        decision = extract_decision(case_data.get("text", ""), case_data)
        case_text = clean_case_text(
            request.case_text or case_data.get("text", ""))

        if not case_text or len(case_text) < 50:
            logger.warning(f"Insufficient text for case_id {request.case_id}")
            fallback_summary = f"{case_name} in {court_name} involved legal proceedings with outcome {decision}."
            return SummaryResponse(summary={
                "case": case_name,
                "court": court_name,
                "issue": fallback_summary,
                "decision": decision,
                "entities": {"persons": [], "organizations": [], "locations": [], "legal_terms": []}
            })

        entities = extract_legal_entities(case_text)
        # For shorter texts, summarize as a single chunk with dynamic length
        if len(case_text) < 1200:
            chunks = [case_text]
        else:
            chunks = chunk_text(case_text)
        if not chunks:
            logger.warning(f"No valid chunks for case_id {request.case_id}")
            fallback_summary = f"{case_name} in {court_name} addressed key legal issues with outcome {decision}."
            return SummaryResponse(summary={
                "case": case_name,
                "court": court_name,
                "issue": fallback_summary,
                "decision": decision,
                "entities": entities
            })

        # Limit to 5 chunks for more detail (or 1 if text is short)
        max_chunks = 1 if len(case_text) < 1200 else 5
        summaries = await asyncio.gather(*(summarize_chunk(chunk) for chunk in chunks[:max_chunks]))
        final_summary = " ".join(summaries)
        words = final_summary.split()
        if len(words) > 400:
            final_summary = " ".join(words[:380]) + "..."
        elif len(words) < 160:
            final_summary += f" The case, {case_name}, in {court_name}, resulted in a {decision.lower()} decision."

        response = SummaryResponse(summary={
            "case": case_name,
            "court": court_name,
            "issue": final_summary,
            "decision": decision,
            "entities": entities
        })

        logger.info(
            f"Generated summary for case_id {request.case_id}: {case_name}")
        return response

    except Exception as e:
        logger.error(f"Error summarizing case_id {request.case_id}: {str(e)}")
        return SummaryResponse(summary={
            "case": "Unknown",
            "court": "Unknown",
            "issue": "Error during summarization.",
            "decision": "Unknown",
            "entities": {"persons": [], "organizations": [], "locations": [], "legal_terms": []}
        })
