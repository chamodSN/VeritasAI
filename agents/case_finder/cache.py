from cachetools import TTLCache
from typing import Any, Optional
from common.config import Config

# 1) search_cache: stores the entire search result set for a given key
# 2) case_cache: stores individual case details by cluster_id


search_cache = TTLCache(maxsize=Config.CACHE_MAX_ITEMS,
                        ttl=Config.CACHE_TTL_SECONDS)
case_cache = TTLCache(maxsize=Config.CACHE_MAX_ITEMS,
                      ttl=Config.CACHE_TTL_SECONDS)


def make_search_key(case_type: str, topic: str, date_from: Optional[str], date_to: Optional[str]) -> str:
    return f"ct={case_type}|tp={topic}|from={date_from or ''}|to={date_to or ''}"


def set_search_result(key: str, value: Any) -> None:
    search_cache[key] = value


def get_search_result(key: str) -> Optional[Any]:
    return search_cache.get(key)


def set_case(cluster_id: str, value: Any) -> None:
    case_cache[cluster_id] = value


def get_case(cluster_id: str) -> Optional[Any]:
    return case_cache.get(cluster_id)
