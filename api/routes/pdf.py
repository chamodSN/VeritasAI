from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File

from core.logging import logger
from api.deps import get_current_user, get_user_repo
from db.user_repository import UserRepository
from services.pdf_service import extract_text_from_pdf, analyze_pdf_text
from services.rate_limiter import check_rate_limit
from api.deps import get_redis
from redis.asyncio import Redis
from datetime import datetime

router = APIRouter()

MAX_PDF_BYTES = 10 * 1024 * 1024  # 10MB


@router.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
    repo: UserRepository = Depends(get_user_repo),
    redis: Redis = Depends(get_redis),
):
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400, detail="Only PDF files are supported")

    await check_rate_limit(redis, user["user_id"])

    contents = await file.read()
    if len(contents) > MAX_PDF_BYTES:
        raise HTTPException(status_code=400, detail="PDF exceeds 10MB limit")

    text = extract_text_from_pdf(contents)
    if not text.strip():
        raise HTTPException(
            status_code=422, detail="Could not extract text from PDF")

    logger.info("pdf_uploaded",
                user=user["user_id"], filename=file.filename, chars=len(text))

    analysis = await analyze_pdf_text(text, user_id=user["user_id"], filename=file.filename)

    await repo.store_results(
        user_id=user["user_id"],
        query=f"[PDF] {file.filename}",
        result=analysis,
        timestamp=datetime.utcnow(),
    )

    return {"filename": file.filename, "analysis": analysis}
