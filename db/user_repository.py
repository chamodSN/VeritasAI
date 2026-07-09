from __future__ import annotations

from datetime import datetime
from typing import Optional, Any
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from core.config import settings
from core.logging import logger

_client: Optional[AsyncIOMotorClient] = None

async def get_database() -> AsyncIOMotorDatabase:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(
            settings.MONGO_URI,
            serverSelectionTimeoutMS=8000,
            maxPoolSize=50,
            minPoolSize=5,
            retryWrites=True,
        )
        logger.info("MongoDB Atlas Connected", db=settings.DATABASE_NAME)

        return _client[settings.DATABASE_NAME]
    
# dependency injection
# Usage:
#   db = await get_database()          # connect once
#   repo = UserRepository(db)          # inject the connection
#   await repo.get_by_email("x@y.com") # use it

class UserRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._users = db["users"]
        self._results = db["results"]

    async def upsert_user(self,user_data: dict[str, Any]) -> None:
        await self._users.update_one(
            {"email": user_data["email"]},
            {"$set": user_data},
            {"$setOnInsert": {"created_at": datetime.utcnow()}},
            upsert=True,
        )

    async def get_by_email(self,email:str) ->Optional[Any]:
        return await self._users.find_one({"email": email}, {"_id": 0})

    async def get_by_id(self,user_id:str) ->Optional[Any]:
        return await self._users.find_one({"user_id": user_id}, {"_id": 0})
    
    async def store_results(self,user_id:str,query:str,result:dict[str,Any],timestamp:datetime,job_id:Optional[str]=None) -> None:
        await self._results.insert_one({
            "user_id": user_id,
            "query": query,
            "result": result,
            "timestamp": timestamp,
            "job_id": job_id
        })

    async def get_results_by_job_id(self,user_id:str,job_id:str) -> Optional[dict]:
        return await self._results.find_one({"user_id": user_id, "job_id": job_id}, {"_id": 0})

    async def get_user_results(self,user_id:str,limit:int=20) -> list[dict]:
        cursor = self._results.find({"user_id": user_id}, {"_id": 1, "query": 1, "timestamp": 1, "result": 1}).sort("timestamp", -1).limit(limit)

        results = []

        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            results.append(doc)
        return results