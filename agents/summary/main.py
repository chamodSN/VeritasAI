from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from transformers import pipeline, AutoTokenizer
import httpx
import re
import asyncio
from concurrent.futures import ThreadPoolExecutor
import torch
from common.security import verify_token
from common.logging import logger
from common.config import Config

app = FastAPI(title="Case Summarization Agent")

# Optimize Model Loading: Use a smaller model and enable mixed precision
try:
    model_name = "sshleifer/distilbart-cnn-6-6"  # Smaller model for faster inference
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    summarizer = pipeline(
        "summarization",
        model=model_name,
        tokenizer=tokenizer,
        device=-1,  # Explicitly use CPU (no GPU available)
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32  # safer on CPU
    )
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

# Use Text-Based Splitting, Reduce Chunk Size
def chunk_text(text: str, max_chars: int = 500) -> list[str]:
    """Split text into smaller chunks based on character count."""
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

# Dynamically adjust summarization length
def get_summary_length(text: str) -> tuple[int, int]:
    input_length = len(tokenizer.encode(text))
    # Make summary shorter than input, but not too small
    max_len = min(250, max(30, input_length // 2))
    min_len = max(10, max_len // 3)
    return min_len, max_len

# Summarize with retries
async def summarize_chunk(chunk: str, attempt: int = 1, max_attempts: int = 2) -> str:
    """Summarize a single chunk with retries and adjusted parameters."""
    try:
        min_len, max_len = get_summary_length(chunk)
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: summarizer(chunk, max_length=max_len, min_length=min_len, do_sample=False)[0]["summary_text"]
        )
        return result
    except Exception as e:
        logger.error(f"Attempt {attempt} - Error summarizing chunk: {str(e)}")
        if attempt < max_attempts:
            await asyncio.sleep(0.5)
            return await summarize_chunk(chunk, attempt + 1, max_attempts)
        return ""

@app.post("/summarize", response_model=SummaryResponse)
async def summarize_case(request: SummaryRequest, token: str = Depends(verify_token)):
    try:
        if not request.case_id or not request.case_id.isdigit():
            logger.error(f"Invalid case_id received: {request.case_id}")
            raise HTTPException(status_code=400, detail="Valid Case ID is required")

        # Fetch case data
        async with httpx.AsyncClient() as client:
            for attempt in range(2):  # Reduce Retries
                try:
                    response = await client.get(
                        f"{Config.COURTLISTENER_BASE_URL}opinions/{request.case_id}/?fields=plain_text,html_lawbox,html_columbia,html,html_with_citations,case_name,disposition,court",
                        headers={"Authorization": f"Token {Config.COURTLISTENER_API_KEY}"}
                    )
                    logger.info(f"Attempt {attempt + 1} - CourtListener API request for case_id {request.case_id}")
                    response.raise_for_status()
                    case_data = response.json()
                    break
                except httpx.HTTPStatusError as e:
                    logger.error(f"Attempt {attempt + 1} - CourtListener API error: {str(e)}")
                    if attempt == 1:
                        raise HTTPException(status_code=e.response.status_code, detail=str(e))
                    await asyncio.sleep(0.5)

        # Extract court name
        court_name = "Unknown"
        if case_data.get("court"):
            try:
                court_resp = await client.get(case_data["court"], headers={"Authorization": f"Token {Config.COURTLISTENER_API_KEY}"})
                court_resp.raise_for_status()
                court_info = court_resp.json()
                court_name = court_info.get("full_name") or court_info.get("name") or "Unknown"
            except Exception as e:
                logger.warning(f"Failed to fetch court details for case_id {request.case_id}: {str(e)}")

        # Extract case name and decision
        case_name = case_data.get("case_name") or "Unknown vs Unknown"
        decision = case_data.get("disposition") or "Unknown"

        # Extract and clean case text
        case_text = (
            case_data.get("plain_text")
            or case_data.get("html_lawbox")
            or case_data.get("html_columbia")
            or case_data.get("html")
            or case_data.get("html_with_citations", "")
        )
        case_text = clean_case_text(case_text)

        if not case_text or len(case_text) < 100:
            logger.error(f"Invalid or too short case text for case_id {request.case_id}")
            raise HTTPException(status_code=422, detail="Case text is empty or too short for summarization")

        # Use Text-Based Splitting, Reduce Chunk Size
        chunks = chunk_text(case_text, max_chars=500)
        if not chunks:
            raise HTTPException(status_code=422, detail="No valid text chunks for summarization")

        # Batch Processing with ThreadPoolExecutor
        max_workers = min(len(chunks), 4)  # Limit to 4 threads to avoid CPU overload
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            summary_tasks = [
                asyncio.get_event_loop().run_in_executor(
                    executor,
                    lambda c=chunk: summarizer(
                        c,
                        max_length=get_summary_length(c)[1],
                        min_length=get_summary_length(c)[0],
                        do_sample=False
                    )[0]["summary_text"]
                )
                for chunk in chunks
            ]
            summaries = await asyncio.gather(*summary_tasks, return_exceptions=True)

        valid_summaries = [s for s in summaries if isinstance(s, str) and s.strip()]
        if not valid_summaries:
            raise HTTPException(status_code=500, detail="Failed to generate any valid summaries")

        final_summary = " ".join(valid_summaries)

        # Build response
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
