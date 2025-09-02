from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from transformers import pipeline, AutoTokenizer
import httpx
import re
import asyncio
from common.security import verify_token
from common.logging import logger
from common.config import Config

app = FastAPI(title="Case Summarization Agent")

# Load Hugging Face model and tokenizer
try:
    model_name = "facebook/bart-large-cnn"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    summarizer = pipeline(
        "summarization", model=model_name, tokenizer=tokenizer)
except Exception as e:
    logger.error(f"Failed to load Hugging Face model: {str(e)}")
    raise Exception("Summarization model initialization failed")


class SummaryRequest(BaseModel):
    case_id: str


class SummaryResponse(BaseModel):
    summary: dict


def clean_case_text(text: str) -> str:
    """Remove HTML tags and excessive whitespace for clean summarization input."""
    text = re.sub(r"<.*?>", "", text)  # Remove HTML tags
    text = re.sub(r"\s+", " ", text).strip()  # Normalize whitespace
    return text


def chunk_text(text: str, max_tokens: int = 512) -> list[str]:
    """Split text into chunks based on token count."""
    tokens = tokenizer(text, truncation=False, return_tensors="pt")[
        "input_ids"][0]
    chunks = []
    current_chunk = []
    current_token_count = 0

    for token in tokens:
        current_chunk.append(token)
        current_token_count += 1
        if current_token_count >= max_tokens:
            chunk_text = tokenizer.decode(
                current_chunk, skip_special_tokens=True)
            chunks.append(chunk_text)
            current_chunk = []
            current_token_count = 0

    if current_chunk:
        chunk_text = tokenizer.decode(current_chunk, skip_special_tokens=True)
        if chunk_text.strip():
            chunks.append(chunk_text)

    return chunks


async def summarize_chunk(chunk: str, attempt: int = 1, max_attempts: int = 3) -> str:
    """Summarize a single chunk with retries."""
    try:
        result = await asyncio.get_event_loop().run_in_executor(
            None, lambda: summarizer(chunk, max_length=200, min_length=50, do_sample=False)[
                0]["summary_text"]
        )
        return result
    except Exception as e:
        logger.error(f"Attempt {attempt} - Error summarizing chunk: {str(e)}")
        if attempt < max_attempts:
            await asyncio.sleep(1)
            return await summarize_chunk(chunk, attempt + 1, max_attempts)
        return ""


@app.post("/summarize", response_model=SummaryResponse)
async def summarize_case(request: SummaryRequest, token: str = Depends(verify_token)):
    try:
        if not request.case_id or not request.case_id.isdigit():
            logger.error(f"Invalid case_id received: {request.case_id}")
            raise HTTPException(
                status_code=400, detail="Valid Case ID is required")

        # Fetch case data with all required fields in one call
        async with httpx.AsyncClient() as client:
            for attempt in range(3):
                try:
                    response = await client.get(
                        f"{Config.COURTLISTENER_BASE_URL}opinions/{request.case_id}/?fields=plain_text,html_lawbox,html_columbia,html,html_with_citations,case_name,disposition,court",
                        headers={
                            "Authorization": f"Token {Config.COURTLISTENER_API_KEY}"}
                    )
                    logger.info(
                        f"Attempt {attempt + 1} - CourtListener API request for case_id {request.case_id}: URL={response.request.url}, Status={response.status_code}")
                    response.raise_for_status()
                    case_data = response.json()
                    break
                except httpx.HTTPStatusError as e:
                    logger.error(
                        f"Attempt {attempt + 1} - CourtListener API error: {str(e)}")
                    if attempt == 2:
                        raise HTTPException(
                            status_code=e.response.status_code, detail=str(e))
                    await asyncio.sleep(1)

        # Extract court name from court field
        court_name = "Unknown"
        if case_data.get("court"):
            try:
                court_resp = await client.get(case_data["court"], headers={"Authorization": f"Token {Config.COURTLISTENER_API_KEY}"})
                court_resp.raise_for_status()
                court_info = court_resp.json()
                court_name = court_info.get(
                    "full_name") or court_info.get("name") or "Unknown"
            except Exception as e:
                logger.warning(
                    f"Failed to fetch court details for case_id {request.case_id}: {str(e)}")

        # Extract case name and decision
        case_name = case_data.get("case_name") or "Unknown vs Unknown"
        decision = case_data.get("disposition") or "Unknown"

        # Extract case text
        case_text = (
            case_data.get("plain_text")
            or case_data.get("html_lawbox")
            or case_data.get("html_columbia")
            or case_data.get("html")
            or case_data.get("html_with_citations", "")
        )
        case_text = clean_case_text(case_text)

        if not case_text or len(case_text) < 100:
            logger.error(
                f"Invalid or too short case text for case_id {request.case_id}: {case_text[:100] if case_text else 'None'}")
            raise HTTPException(
                status_code=422, detail="Case text is empty or too short for summarization")

        # Summarize chunks in parallel
        chunks = chunk_text(case_text, max_tokens=512)
        if not chunks:
            raise HTTPException(
                status_code=422, detail="No valid text chunks for summarization")

        summary_tasks = [summarize_chunk(chunk) for chunk in chunks]
        summaries = await asyncio.gather(*summary_tasks, return_exceptions=True)

        valid_summaries = [
            s for s in summaries if isinstance(s, str) and s.strip()]
        if not valid_summaries:
            raise HTTPException(
                status_code=500, detail="Failed to generate any valid summaries")

        final_summary = " ".join(valid_summaries)

        # Build response
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
        raise HTTPException(status_code=500, detail=str(e))