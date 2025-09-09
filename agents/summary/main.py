# summary/main.py
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from transformers import pipeline, AutoTokenizer
import httpx
import re
import asyncio
import torch
import logging
from common.security import verify_token
from common.logging import logger
from common.config import Config
from common.models import SummaryRequest, SummaryResponse
from fastapi.middleware.cors import CORSMiddleware

logging.getLogger("transformers").setLevel(logging.ERROR)

app = FastAPI(title="Case Summarization Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

try:
    model_name = "sshleifer/distilbart-cnn-6-6"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    summarizer = pipeline(
        "summarization",
        model=model_name,
        tokenizer=tokenizer,
        device=-1,
        torch_dtype=torch.float32
    )
    classifier = pipeline("zero-shot-classification",
                          model="facebook/bart-large-mnli")
    logger.info(
        "Summarization model and zero-shot classifier loaded successfully")
except Exception as e:
    logger.error(f"Failed to load Hugging Face model: {str(e)}")
    raise Exception("Summarization model initialization failed")


def clean_case_text(text: str) -> str:
    text = re.sub(r"<.*?>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"[^\x00-\x7F]+", "", text)  # Remove non-ASCII characters
    return text


def chunk_text(text: str, max_chars: int = 500) -> list[str]:
    words = text.split()
    chunks = []
    current_chunk = []
    current_length = 0
    for word in words:
        current_chunk.append(word)
        current_length += len(word) + 1
        if current_length >= max_chars:
            chunks.append(" ".join(current_chunk))
            current_chunk = []
            current_length = 0
    if current_chunk:
        chunks.append(" ".join(current_chunk))
    return [chunk for chunk in chunks if len(chunk) > 50]


def get_token_count(text: str) -> int:
    try:
        tokens = tokenizer(text, truncation=False, return_tensors="pt")[
            "input_ids"][0]
        return len(tokens)
    except Exception as e:
        logger.error(f"Error counting tokens: {str(e)}")
        return 0


async def summarize_chunk(chunk: str, attempt: int = 1, max_attempts: int = 2) -> str:
    try:
        input_length = get_token_count(chunk)
        max_length = max(25, min(input_length // 2, 150))
        min_length = max(10, max_length // 4)
        logger.debug(
            f"Summarizing chunk: input_length={input_length}, max_length={max_length}, min_length={min_length}")
        result = summarizer(chunk, max_length=max_length,
                            min_length=min_length, do_sample=False)[0]["summary_text"]
        return result
    except Exception as e:
        logger.error(f"Attempt {attempt} - Error summarizing chunk: {str(e)}")
        if attempt < max_attempts:
            await asyncio.sleep(0.5)
            return await summarize_chunk(chunk, attempt + 1, max_attempts)
        return ""


def extract_case_name(text: str, case_data: dict) -> str:
    for field in ["caseNameFull", "case_name", "caseName", "caseNameShort", "docketNumber"]:
        if case_data.get(field):
            return case_data[field]
    match = re.search(
        r"([\w\s&,\.]+)\s+v\.\s+([\w\s&,\.]+)", text, re.IGNORECASE)
    return f"{match.group(1).strip()} v. {match.group(2).strip()}" if match else "Unknown vs Unknown"


def extract_court(text: str, case_data: dict) -> str:
    court = case_data.get("court_citation_string", case_data.get(
        "court", "United States Supreme Court"))
    if court != "Unknown":
        return court
    match = re.search(
        r"(Supreme Court|Court of Appeals|Circuit Court|District Court)[\w\s]*", text, re.IGNORECASE)
    return match.group(1).capitalize() if match else "United States Supreme Court"


def extract_decision(text: str, case_data: dict) -> str:
    decision = case_data.get("disposition", case_data.get("status", "Unknown"))
    if decision != "Unknown":
        return decision
    last_part = text[-1000:]
    match = re.search(
        r"(affirmed|reversed|remanded|dismissed|granted|denied)", last_part, re.IGNORECASE)
    return match.group(1).capitalize() if match else "Unknown"


async def fetch_case_data(case_id: str, client: httpx.AsyncClient) -> dict:
    try:
        response = await client.get(
            f"{Config.COURTLISTENER_BASE_URL}opinions/?cluster={case_id}&fields=plain_text,html_lawbox,html_columbia,html,html_with_citations,caseName,caseNameFull,caseNameShort,disposition,court_citation_string,docketNumber,status",
            headers={"Authorization": f"Token {Config.COURTLISTENER_API_KEY}"}
        )
        response.raise_for_status()
        opinions = response.json().get("results", [])
        data = opinions[0] if opinions else {}
        cluster_response = await client.get(
            f"{Config.COURTLISTENER_BASE_URL}clusters/{case_id}/?fields=case_name,case_name_short,disposition,court_name,docket_number,court_id",
            headers={"Authorization": f"Token {Config.COURTLISTENER_API_KEY}"}
        )
        cluster_response.raise_for_status()
        cluster_data = cluster_response.json()
        data.update({
            "caseName": cluster_data.get("case_name", data.get("caseName", "")),
            "caseNameFull": cluster_data.get("case_name", data.get("caseNameFull", "")),
            "caseNameShort": cluster_data.get("case_name_short", data.get("caseNameShort", "")),
            "disposition": cluster_data.get("disposition", data.get("disposition", "")),
            "court_citation_string": cluster_data.get("court_name", data.get("court_citation_string", "")),
            "court_id": cluster_data.get("court_id", data.get("court_id", "")),
            "docketNumber": cluster_data.get("docket_number", data.get("docketNumber", ""))
        })
        return data
    except httpx.HTTPStatusError as e:
        logger.error(
            f"CourtListener API error for case_id {case_id}: {str(e)}")
        return {}
    except Exception as e:
        logger.error(
            f"Error fetching case data for case_id {case_id}: {str(e)}")
        return {}


@app.post("/summarize", response_model=SummaryResponse)
async def summarize_case(request: SummaryRequest, token: dict = Depends(verify_token)):
    try:
        if not request.case_id or not request.case_id.isdigit():
            logger.error(f"Invalid case_id: {request.case_id}")
            raise HTTPException(
                status_code=400, detail="Valid case_id required")

        async with httpx.AsyncClient(timeout=30) as client:
            case_data = request.case_data or await fetch_case_data(request.case_id, client)
            logger.debug(
                f"Case data for case_id {request.case_id}: {case_data}")

        if not isinstance(case_data, dict):
            logger.error(
                f"Invalid case_data format for case_id {request.case_id}")
            raise HTTPException(
                status_code=400, detail="Invalid case_data format")

        case_name = extract_case_name("", case_data)
        court_name = extract_court("", case_data)
        decision = extract_decision("", case_data)

        case_text = (
            case_data.get("plain_text") or
            case_data.get("html_lawbox") or
            case_data.get("html_columbia") or
            case_data.get("html") or
            case_data.get("html_with_citations") or
            ""
        )
        case_text = clean_case_text(case_text)

        if not case_text or len(case_text) < 50:
            logger.warning(
                f"No valid text for case_id {request.case_id}, using LLM fallback")
            fallback_text = f"Generate a summary for case {case_name} in {court_name} involving cyber fraud."
            summary_result = summarizer(fallback_text, max_length=100, min_length=30)[
                0]["summary_text"]
            return SummaryResponse(summary={
                "case": case_name,
                "court": court_name,
                "issue": summary_result,
                "decision": decision
            })

        if case_name == "Unknown vs Unknown":
            case_name = extract_case_name(case_text[:2000], case_data)
        if court_name == "Unknown":
            court_name = extract_court(case_text, case_data)
        if decision == "Unknown":
            result = classifier(case_text[-500:], candidate_labels=[
                                "affirmed", "reversed", "remanded", "dismissed", "granted", "denied"])
            decision = result['labels'][0].capitalize()

        logger.debug(
            f"Extracted: case_name={case_name}, court_name={court_name}, decision={decision}")

        chunks = chunk_text(case_text, max_chars=500)
        if not chunks:
            logger.warning(f"No valid chunks for case_id {request.case_id}")
            return SummaryResponse(summary={
                "case": case_name,
                "court": court_name,
                "issue": "No valid text chunks for summarization",
                "decision": decision
            })

        summaries = []
        for chunk in chunks:
            summary = await summarize_chunk(chunk)
            if summary:
                summaries.append(summary)

        if not summaries:
            logger.warning(
                f"No valid summaries generated for case_id {request.case_id}")
            return SummaryResponse(summary={
                "case": case_name,
                "court": court_name,
                "issue": "Failed to generate summary",
                "decision": decision
            })

        final_summary = " ".join(summaries)
        response = SummaryResponse(summary={
            "case": case_name,
            "court": court_name,
            "issue": final_summary,
            "decision": decision
        })

        logger.info(
            f"Generated summary for case_id {request.case_id}: {case_name}")
        return response

    except httpx.HTTPStatusError as e:
        logger.error(
            f"CourtListener API error for case_id {request.case_id}: {str(e)}")
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        logger.error(f"Error summarizing case_id {request.case_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Summary error: {str(e)}")