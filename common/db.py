# common/db.py (No changes necessary; now points to MongoDB Atlas via .env URI)
from pymongo import MongoClient
from datetime import datetime
from common.config import Config
from common.logging import logger


class MongoDB:
    _client = None
    _db = None

    @classmethod
    def get_client(cls):
        if cls._client is None:
            cls._client = MongoClient(Config.MONGO_URI)
            logger.info("MongoDB connected")
        return cls._client

    @classmethod
    def get_db(cls):
        if cls._db is None:
            cls._db = cls.get_client()[Config.MONGO_DB_NAME]
        return cls._db

    @classmethod
    async def store_query_result(cls, user_id: str, query: str, results: dict):
        collection = cls.get_db()["query_results"]
        document = {"user_id": user_id, "query": query,
                    "results": results, "timestamp": datetime.utcnow()}
        collection.insert_one(document)
        logger.info(f"Stored result for query: {query}")

    @classmethod
    async def get_query_result(cls, user_id: str, query: str):
        collection = cls.get_db()["query_results"]
        return collection.find_one({"user_id": user_id, "query": query})
