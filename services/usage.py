from __future__ import annotations

from datetime import datetime, date, timedelta
from typing import List

from core.logging import logger

_PRICING = {
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o":      {"input": 2.50, "output": 10.00},
    "gpt-4":       {"input": 30.0, "output": 60.00},
}


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:

    # fall back to gpt-4o-mini pricing
    pricing = _PRICING.get(model, _PRICING["gpt-4o-mini"])

    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]

    return round(input_cost + output_cost, 6)


class UsageTracker:

    def __init__(self) -> None:
        self._db = None  # lazy initialization

    async def _get_collection(self):

        from db.user_repository import get_database

        if self._db is None:
            self._db = (await get_database())["usage"]
        return self._db

    async def record(self, user_id: str, request_id: str, agent_name: str, model: str,
                     input_tokens: int, output_tokens: int) -> None:

        cost = calculate_cost(model, input_tokens, output_tokens)
        today = date.today().isoformat()

        try:
            collection = await self._get_collection()

            await collection.update_one(
                {
                    "user_id": user_id,
                    "date": today,
                },
                {
                    "$inc": {
                        "total_input_tokens": input_tokens,
                        "total_output_tokens": output_tokens,
                        "total_cost_usd": cost,
                        "total_requests": 1,
                        f"agents.{agent_name}.input_tokens": input_tokens,
                        f"agents.{agent_name}.output_tokens": output_tokens,
                        f"agents.{agent_name}.cost_usd": cost,
                    },
                    "$set": {
                        f"agents.{agent_name}.last_request_id": request_id,
                    },
                    "$push": {
                        "request_ids": {
                            "$each": [request_id],
                            "$slice": -50,  # keep only the most recent 50 per day
                        }
                    },
                    "$setOnInsert": {"created_at": datetime.utcnow()},
                },
                upsert=True,
            )

            logger.debug(
                "usage_recorded",
                user=user_id,
                agent=agent_name,
                tokens=input_tokens + output_tokens,
                cost_usd=cost,
            )

        except Exception as exc:
            logger.warning("usage_record_failed", error=str(exc))

    async def get_user_usage(self, user_id: str, days: int = 30) -> List[dict]:
        cutoff = (date.today() - timedelta(days=days)).isoformat()

        try:
            collection = await self._get_collection()
            cursor = collection.find(
                {"user_id": user_id, "date": {"$gte": cutoff}},
                {"_id": 0},
            ).sort("date", -1)
            return [doc async for doc in cursor]

        except Exception as exc:
            logger.warning("usage_fetch_failed", error=str(exc))
            return []


usage_tracker = UsageTracker()
