from __future__ import annotations

from datetime import datetime

from core.logging import logger
from db.user_repository import get_database


async def save_user_alert(user_id: str, name: str, query: str, rate: str, resource_uri: str) -> None:
    db = await get_database()
    await db["alerts"].insert_one({
        "user_id": user_id,
        "name": name,
        "query": query,
        "rate": rate,
        "resource_uri": resource_uri,
        "created_at": datetime.utcnow(),
    })
    logger.info("alert_saved", user=user_id, name=name)


async def list_user_alerts(user_id: str) -> list[dict]:
    db = await get_database()
    cursor = db["alerts"].find({"user_id": user_id}, {"_id": 0})
    return [doc async for doc in cursor]


async def remove_user_alert(user_id: str, alert_id: int) -> None:
    db = await get_database()
    await db["alerts"].delete_many({
        "user_id": user_id,
        "resource_uri": {"$regex": f"/{alert_id}/$"},
    })
