from __future__ import annotations

import json
from datetime import timedelta

from arq import create_pool
from arq.connections import RedisSettings
from redis.asyncio import Redis, from_url

from core.config import settings
from core.logging import logger

JOB_RESULT_PREFIX = "veritasai:job_result:"
JOB_STATUS_PREFIX = "veritasai:job_status:"
JOB_TTL = timedelta(hours=2)


async def get_redis_pool() -> Redis:
    return from_url(settings.REDIS_URL, decode_responses=True)


async def close_redis_pool(redis: Redis) -> None:
    await redis.aclose()


async def enqueue_analysis_job(redis: Redis, job_id: str, query: str, user_id: str,
                               prior_context: str | None = None) -> None:
    await redis.set(f"{JOB_STATUS_PREFIX}{job_id}", "pending", ex=int(JOB_TTL.total_seconds()))

    arq_pool = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))
    try:
        await arq_pool.enqueue_job(
            "run_analysis_job",
            job_id,
            query,
            user_id,
            prior_context,
        )
    finally:
        await arq_pool.aclose()


async def get_job_result(redis: Redis, job_id: str) -> tuple[str, dict | None]:
    status = await redis.get(f"{JOB_STATUS_PREFIX}{job_id}")
    if status is None:
        return "not_found", None

    if status != "completed":
        return status, None

    raw = await redis.get(f"{JOB_RESULT_PREFIX}{job_id}")
    result = json.loads(raw) if raw else None
    return status, result


async def mark_job_completed(redis: Redis, job_id: str, result: dict) -> None:
    await redis.set(
        f"{JOB_RESULT_PREFIX}{job_id}",
        json.dumps(result, default=str),
        ex=int(JOB_TTL.total_seconds()),
    )
    await redis.set(f"{JOB_STATUS_PREFIX}{job_id}", "completed", ex=int(JOB_TTL.total_seconds()))


async def mark_job_failed(redis: Redis, job_id: str) -> None:
    await redis.set(f"{JOB_STATUS_PREFIX}{job_id}", "failed", ex=int(JOB_TTL.total_seconds()))

# ARQ worker entrypoint (run with: arq services.queue.WorkerSettings)


async def run_analysis_job(ctx, job_id: str, query: str, user_id: str, prior_context: str | None):
    from graph.pipeline import run_pipeline  # local import avoids circular import

    redis: Redis = ctx["redis_client"]
    try:
        result = await run_pipeline(query=query, user_id=user_id, request_id=job_id,
                                    prior_context=prior_context)
        await mark_job_completed(redis, job_id, result)
        logger.info("analysis_job_completed", job_id=job_id)
    except Exception as exc:
        logger.error("analysis_job_failed", job_id=job_id, error=str(exc))
        await mark_job_failed(redis, job_id)


async def startup(ctx):
    ctx["redis_client"] = await get_redis_pool()


async def shutdown(ctx):
    await close_redis_pool(ctx["redis_client"])


class WorkerSettings:
    functions = [run_analysis_job]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    max_jobs = 5
    job_timeout = 300
