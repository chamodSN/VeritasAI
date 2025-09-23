# cache.py (no changes needed)

import json
import hashlib
import asyncio
from typing import Any, Dict, Optional
from datetime import timedelta

from redis.asyncio import Redis
from common.config import Config

_redis: Optional[Redis] = None
_lock = asyncio.Lock()  # protects lazy init only


def _ns(*parts: str) -> str:
    return ":".join([Config.CACHE_PREFIX, *parts])


async def _get_client() -> Redis:
    global _redis
    if _redis is None:
        async with _lock:
            if _redis is None:
                _redis = Redis.from_url(
                    Config.REDIS_URL, encoding="utf-8", decode_responses=True)
    return _redis



def make_search_key(user_id: str, case_type: str, topic: str, date_from: Optional[str], date_to: Optional[str]) -> str:
    # keep your old structure but scope by user
    base = f"ct={case_type or ''}|tp={topic or ''}|from={date_from or ''}|to={date_to or ''}"
    digest = hashlib.sha1(base.encode("utf-8")).hexdigest()  # short & safe
    return _ns("search", f"user:{user_id}", digest)


def search_namespace(key: str) -> str:
    return _ns("search", key)


def case_key(cluster_id: str) -> str:
    return _ns("case", cluster_id)


def summary_key(cache_key: str) -> str:
    return _ns("summary", cache_key)


def citations_key(cache_key: str) -> str:
    return _ns("citations", cache_key)



async def set_search_result(cache_key: str, data: Dict[str, Any], ttl_seconds: Optional[int] = None) -> None:
    r = await _get_client()
    await r.set(cache_key, json.dumps(data), ex=ttl_seconds or Config.CACHE_TTL_SECONDS)


async def get_search_result(cache_key: str) -> Optional[Dict[str, Any]]:
    r = await _get_client()
    val = await r.get(cache_key)
    return json.loads(val) if val else None


async def set_case(cluster_id: str, data: Dict[str, Any], ttl_seconds: Optional[int] = None) -> None:
    r = await _get_client()
    await r.set(case_key(cluster_id), json.dumps(data), ex=ttl_seconds or Config.CACHE_TTL_SECONDS)


async def get_case(cluster_id: str) -> Optional[Dict[str, Any]]:
    r = await _get_client()
    val = await r.get(case_key(cluster_id))
    return json.loads(val) if val else None


async def set_summary(cache_key: str, data: Dict[str, Any], ttl_seconds: Optional[int] = None) -> None:
    r = await _get_client()
    await r.set(summary_key(cache_key), json.dumps(data), ex=ttl_seconds or Config.CACHE_TTL_SECONDS)


async def get_summary(cache_key: str) -> Optional[Dict[str, Any]]:
    r = await _get_client()
    val = await r.get(summary_key(cache_key))
    return json.loads(val) if val else None


async def set_citations(cache_key: str, data: Dict[str, Any], ttl_seconds: Optional[int] = None) -> None:
    r = await _get_client()
    await r.set(citations_key(cache_key), json.dumps(data), ex=ttl_seconds or Config.CACHE_TTL_SECONDS)


async def get_citations(cache_key: str) -> Optional[Dict[str, Any]]:
    r = await _get_client()
    val = await r.get(citations_key(cache_key))
    return json.loads(val) if val else None


async def acquire_lock(lock_name: str, ttl_seconds: int = 15) -> bool:
    """
    Return True if acquired. Auto-expires to avoid deadlocks.
    """
    r = await _get_client()
    # NX + EX implements "SET if Not eXists" with expiry
    return await r.set(_ns("lock", lock_name), "1", nx=True, ex=ttl_seconds) is True


async def release_lock(lock_name: str) -> None:
    r = await _get_client()
    await r.delete(_ns("lock", lock_name))