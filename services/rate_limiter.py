# Path: services/rate_limiter.py
from __future__ import annotations

from fastapi import HTTPException, status
from redis.asyncio import Redis

RATE_LIMIT_WINDOW_SECONDS = 60 * 60  # 1 hour
RATE_LIMIT_MAX_REQUESTS = 30
RATE_LIMIT_PREFIX = "veritasai:rate_limit:"


async def check_rate_limit(redis: Redis, user_id: str) -> None:
    key = f"{RATE_LIMIT_PREFIX}{user_id}"
    current = await redis.incr(key)
    if current == 1:
        await redis.expire(key, RATE_LIMIT_WINDOW_SECONDS)

    if current > RATE_LIMIT_MAX_REQUESTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: {RATE_LIMIT_MAX_REQUESTS} requests per hour.",
        )
