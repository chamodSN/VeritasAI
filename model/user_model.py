from pymongo import MongoClient
from common.config import Config
from datetime import datetime

client = MongoClient(Config.MONGO_URI)
db = client[Config.DATABASE_NAME]

users_collection = db['users']
queries_collection = db['queries']
results_collection = db['results']


def store_user(user_info: dict):
    """Store or update user information in MongoDB."""
    # Use upsert to update existing user or insert new one
    users_collection.update_one(
        {"email": user_info["email"]},
        {"$set": user_info},
        upsert=True
    )


def get_user_by_email(email: str):
    """Get user by email address."""
    return users_collection.find_one({"email": email})


def get_user_by_id(user_id: str):
    """Get user by user ID."""
    return users_collection.find_one({"user_id": user_id})


def store_query(user_id: str, query: dict):
    queries_collection.insert_one({"user_id": user_id, **query})


def store_result(user_id: str, result: dict):
    # Convert CrewOutput objects to strings for MongoDB storage
    serialized_result = {}
    for key, value in result.items():
        if hasattr(value, 'raw'):  # CrewOutput object
            serialized_result[key] = str(value.raw)
        else:
            serialized_result[key] = value

    results_collection.insert_one({"user_id": user_id, **serialized_result})


def get_user_queries(user_id: str):
    return list(queries_collection.find({"user_id": user_id}))
