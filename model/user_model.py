from pymongo import MongoClient
from common.config import Config
from common.encryption import secure_storage
from datetime import datetime

client = MongoClient(Config.MONGO_URI)
db = client[Config.DATABASE_NAME]

users_collection = db['users']
queries_collection = db['queries']
results_collection = db['results']


def store_user(user_info: dict):
    """Store or update user information in MongoDB with encryption."""
    # Encrypt all sensitive user data
    encrypted_user_info = {
        "email": user_info["email"],  # Keep email unencrypted for lookup
        "user_id": user_info["user_id"],
        "encrypted_data": secure_storage.store_user_query(
            user_info["user_id"],
            user_info.get("name", "") + "|" + user_info.get("picture", "")
        )["encrypted_data"],
        "encryption_version": "1.0",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    # Use upsert to update existing user or insert new one
    users_collection.update_one(
        {"email": user_info["email"]},
        {"$set": encrypted_user_info},
        upsert=True
    )


def get_user_by_email(email: str):
    """Get user by email address."""
    return users_collection.find_one({"email": email})


def get_user_by_id(user_id: str):
    """Get user by user ID."""
    return users_collection.find_one({"user_id": user_id})


def store_query(user_id: str, query: dict):
    """Store encrypted user query."""
    encrypted_query = secure_storage.store_user_query(user_id, query["query"])
    queries_collection.insert_one({
        "user_id": user_id, 
        "encrypted_data": encrypted_query["encrypted_data"],
        "encryption_version": encrypted_query["encryption_version"],
        "timestamp": query["timestamp"]
    })


def store_result(user_id: str, result: dict):
    """Store encrypted analysis result."""
    # Convert CrewOutput objects to strings for MongoDB storage
    serialized_result = {}
    for key, value in result.items():
        if hasattr(value, 'raw'):  # CrewOutput object
            serialized_result[key] = str(value.raw)
        else:
            serialized_result[key] = value

    results_collection.insert_one({"user_id": user_id, **serialized_result})


def get_user_queries(user_id: str):
    """Get user's encrypted queries from MongoDB."""
    return list(queries_collection.find({"user_id": user_id}))


def get_user_results(user_id: str):
    """Get user's encrypted results from MongoDB"""
    return list(results_collection.find({"user_id": user_id}))
