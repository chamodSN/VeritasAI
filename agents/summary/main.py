from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from transformers import pipeline, AutoTokenizer
import httpx
import re
import asyncio
from concurrent.futures import ThreadPoolExecutor
import torch
import logging
import json
from common.security import verify_token
from common.logging import logger
from common.config import Config

# Suppress transformers warnings
logging.getLogger("transformers").setLevel(logging.ERROR)

app = FastAPI(title="Case Summarization Agent")

try:
    model_name = "sshleifer/distilbart-cnn-6-6"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    summarizer = pipeline(
        "summarization",
        model=model_name,
        tokenizer=tokenizer,
        device=-1,
        torch_dtype=torch.bfloat16
    )
except Exception as e:
    logger.error(f"Failed to load Hugging Face model: {str(e)}")
    raise Exception("Summarization model initialization failed")

class SummaryRequest(BaseModel):
    case_id: str

class SummaryResponse(BaseModel):
    summary: dict

def clean_case_text(text: str) -> str:
    text = re.sub(r"<.*?>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
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
    return chunks

def get_token_count(text: str) -> int:
    tokens = tokenizer(text, truncation=False, return_tensors="pt")["input_ids"][0]
    return len(tokens)

async def summarize_chunk(chunk: str, attempt: int = 1, max_attempts: int = 2) -> str:
    try:
        input_length = get_token_count(chunk)
        max_length = max(25, input_length // 2)
        min_length = max(10, max_length // 4)
        logger.debug(f"Summarizing chunk with input_length={input_length}, max_length={max_length}, min_length={min_length}")
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: summarizer(chunk, max_length=max_length, min_length=min_length, do_sample=False)[0]["summary_text"]
        )
        return result
    except Exception as e:
        logger.error(f"Attempt {attempt} - Error summarizing chunk: {str(e)}")
        if attempt < max_attempts:
            await asyncio.sleep(0.5)
            return await summarize_chunk(chunk, attempt + 1, max_attempts)
        return ""

def extract_case_name(text: str) -> str:
    # Pattern for "A v. B"
    match = re.search(r"([\w\s&,\.]+) v\. ([\w\s&,\.]+)", text, re.IGNORECASE)
    if match:
        return match.group(1).strip() + " v. " + match.group(2).strip()

    # Pattern for "The complainant(s) A ... defendant B"
    match = re.search(r"The complainant[s]? ([\w\s&,\.]+) .+ defendant ([\w\s&,\.]+)", text, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip() + " v. " + match.group(2).strip()

    # Additional pattern for "The complainant A is ... The complainants B and C"
    match = re.search(r"The complainant ([\w\s&,\.]+) is .+ The complainants ([\w\s&,\.]+) are .+ defendant ([\w\s&,\.]+)", text, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip() + ", " + match.group(2).strip() + " v. " + match.group(3).strip()

    return "Unknown vs Unknown"

def extract_court(text: str) -> str:
    # Pattern for court names
    match = re.search(r"(\w+ Court of [\w\s]+|Supreme Court|Court of Appeals|Chancery Court|N\.J\. [\w\s]+|New Jersey [\w\s]+ Court|Few Jersey)", text, re.IGNORECASE)
    if match:
        court = match.group(1)
        if court.lower() == "few jersey":
            return "New Jersey Court of Chancery"  # Correct OCR typo
        return court
    return "Unknown"

def extract_decision(text: str) -> str:
    # Look in the last 1000 characters for decision keywords
    last_part = text[-1000:]
    match = re.search(r"(bill must be dismissed|claim dismissed|judgment affirmed|reversed|remanded|denied|granted|conclusion is that [\w\s\.]+)", last_part, re.IGNORECASE)
    if match:
        return match.group(1).capitalize()
    return "Unknown"

@app.post("/summarize", response_model=SummaryResponse)
async def summarize_case(request: SummaryRequest, token: str = Depends(verify_token)):
    try:
        if not request.case_id or not request.case_id.isdigit():
            logger.error(f"Invalid case_id received: {request.case_id}")
            raise HTTPException(status_code=400, detail="Valid Case ID is required")

        async with httpx.AsyncClient() as client:
            for attempt in range(2):
                try:
                    response = await client.get(
                        f"{Config.COURTLISTENER_BASE_URL}opinions/{request.case_id}/?fields=plain_text,html_lawbox,html_columbia,html,html_with_citations,case_name,caseName,caseNameFull,caseNameShort,disposition,court,court_citation_string,status,docketNumber,snippet",
                        headers={"Authorization": f"Token {Config.COURTLISTENER_API_KEY}"}
                    )
                    logger.info(f"Attempt {attempt + 1} - CourtListener API request for case_id {request.case_id}")
                    response.raise_for_status()
                    case_data = response.json()
                    logger.debug(f"API response for case_id {request.case_id}: {json.dumps(case_data, indent=2)}")
                    break
                except httpx.HTTPStatusError as e:
                    logger.error(f"Attempt {attempt + 1} - CourtListener API error: {str(e)}")
                    if attempt == 1:
                        raise HTTPException(status_code=e.response.status_code, detail=str(e))
                    await asyncio.sleep(0.5)

        # Extract court name with fallbacks
        court_name = case_data.get("court_citation_string") or "Unknown"
        if case_data.get("court") and court_name == "Unknown":
            try:
                court_resp = await client.get(case_data["court"], headers={"Authorization": f"Token {Config.COURTLISTENER_API_KEY}"})
                court_resp.raise_for_status()
                court_info = court_resp.json()
                court_name = (
                    court_info.get("full_name") or
                    court_info.get("name") or
                    "Unknown"
                )
            except Exception as e:
                logger.warning(f"Failed to fetch court details for case_id {request.case_id}: {str(e)}")

        # Extract case name with fallbacks
        case_name = (
            case_data.get("caseNameFull") or
            case_data.get("case_name") or
            case_data.get("caseName") or
            case_data.get("caseNameShort") or
            case_data.get("docketNumber") or
            "Unknown vs Unknown"
        )

        # Extract decision with fallback
        decision = case_data.get("disposition") or case_data.get("status") or "Unknown"

        case_text = (
            case_data.get("plain_text") or
            case_data.get("html_lawbox") or
            case_data.get("html_columbia") or
            case_data.get("html") or
            case_data.get("html_with_citations") or ""
        )
        case_text = clean_case_text(case_text)

        # Fallback extraction from case_text if API fields are missing
        if case_name == "Unknown vs Unknown":
            case_name = extract_case_name(case_text[:2000])  # Limit to first 2000 chars for efficiency

        if court_name == "Unknown":
            court_name = extract_court(case_text)

        if decision == "Unknown":
            decision = extract_decision(case_text)

        # Log extracted fields for debugging
        logger.debug(f"Extracted fields for case_id {request.case_id}: case_name={case_name}, court_name={court_name}, decision={decision}")

        if not case_text or len(case_text) < 100:
            logger.error(f"Invalid or too short case text for case_id {request.case_id}")
            raise HTTPException(status_code=422, detail="Case text is empty or too short for summarization")

        chunks = chunk_text(case_text, max_chars=500)
        if not chunks:
            raise HTTPException(status_code=422, detail="No valid text chunks for summarization")

        max_workers = min(len(chunks), 4)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            summary_tasks = [
                asyncio.get_event_loop().run_in_executor(
                    executor,
                    lambda c=chunk: summarizer(c, max_length=max(25, get_token_count(c) // 2), min_length=max(10, (max(25, get_token_count(c) // 2)) // 4), do_sample=False)[0]["summary_text"]
                )
                for chunk in chunks
            ]
            summaries = await asyncio.gather(*summary_tasks, return_exceptions=True)

        valid_summaries = [s for s in summaries if isinstance(s, str) and s.strip()]
        if not valid_summaries:
            raise HTTPException(status_code=500, detail="Failed to generate any valid summaries")

        final_summary = " ".join(valid_summaries)

        response = SummaryResponse(summary={
            "case": case_name,
            "court": court_name,
            "issue": final_summary,
            "decision": decision
        })

        logger.info(f"Generated summary for case_id {request.case_id}: {case_name}")
        return response

    except httpx.HTTPStatusError as e:
        logger.error(f"CourtListener API error for case_id {request.case_id}: {str(e)}")
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        logger.error(f"Error summarizing case_id {request.case_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))