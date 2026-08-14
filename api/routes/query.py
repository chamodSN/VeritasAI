# Path: api/routes/query.py
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from redis.asyncio import Redis

from core.logging import logger
from api.deps import get_current_user, get_user_repo, get_redis
from db.user_repository import UserRepository
from services.cache import get_cached_result, set_cached_result, make_query_hash
from services.rate_limiter import check_rate_limit
from services.research_session import get_prior_context
from services.queue import enqueue_analysis_job, get_job_result

router = APIRouter()


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=2000)


@router.post("/query")
async def submit_query(
    payload: QueryRequest,
    user: dict = Depends(get_current_user),
    repo: UserRepository = Depends(get_user_repo),
    redis: Redis = Depends(get_redis),
):
    await check_rate_limit(redis, user["user_id"])

    query_hash = make_query_hash(payload.query)
    cached = await get_cached_result(redis, query_hash)
    if cached:
        await repo.store_results(
            user_id=user["user_id"],
            query=payload.query,
            result=cached,
            timestamp=datetime.utcnow(),
        )
        return {"status": "completed", "result": cached}

    job_id = str(uuid.uuid4())
    prior_context = await get_prior_context(repo, user["user_id"], payload.query)

    await enqueue_analysis_job(
        redis,
        job_id=job_id,
        query=payload.query,
        user_id=user["user_id"],
        prior_context=prior_context,
    )

    logger.info("query_job_enqueued", job_id=job_id, user=user["user_id"])
    return {"status": "pending", "job_id": job_id}


@router.get("/query/status/{job_id}")
async def query_status(
    job_id: str,
    redis: Redis = Depends(get_redis),
    repo: UserRepository = Depends(get_user_repo),
    user: dict = Depends(get_current_user),
):
    status, result = await get_job_result(redis, job_id)

    if status == "completed" and result:
        query_hash = make_query_hash(result.get("query", ""))
        await set_cached_result(redis, query_hash, result)
        await repo.store_results(
            user_id=user["user_id"],
            query=result.get("query", ""),
            result=result,
            timestamp=datetime.utcnow(),
            job_id=job_id,
        )

    return {"status": status, "result": result}


@router.get("/user/history")
async def user_history(
    limit: int = 20,
    user: dict = Depends(get_current_user),
    repo: UserRepository = Depends(get_user_repo),
):
    results = await repo.get_user_results(user["user_id"], limit=limit)
    history = [
        {
            "id": r["_id"],
            "query": r["query"],
            "timestamp": r["timestamp"],
            "cases_analyzed": r.get("result", {}).get("cases_analyzed", 0),
        }
        for r in results
    ]
    return {"queries": history}
