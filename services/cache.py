from __future__ import annotations

import hashlib
import json

from redis.asyncio import Redis

CACHE_TTL_SECONDS = 60 * 60 * 6  # 6 hours
CACHE_PREFIX = "veritasai:query_cache:"


def make_query_hash(query: str) -> str:
    normalized = " ".join(query.strip().lower().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


async def get_cached_result(redis: Redis, query_hash: str) -> dict | None:
    raw = await redis.get(f"{CACHE_PREFIX}{query_hash}")
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return None


async def set_cached_result(redis: Redis, query_hash: str, result: dict) -> None:
    await redis.set(
        f"{CACHE_PREFIX}{query_hash}",
        json.dumps(result, default=str),
        ex=CACHE_TTL_SECONDS,
    )
