from Motor import AsyncIOMotorClient, AsyncIOMotorDatabase
from typing import Optional

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
