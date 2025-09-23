# common/config.py (No changes necessary, but confirmed MONGO_URI points to Atlas; user will update .env)
"""Configuration module to manage environment variables for the application."""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Configuration class to manage environment variables."""
    HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")
    COURTLISTENER_API_KEY = os.getenv("COURTLISTENER_API_KEY")
    COURTLISTENER_BASE_URL = os.getenv(
        "COURTLISTENER_BASE_URL", "https://www.courtlistener.com/api/rest/v4/")
    CASE_FINDER_URL = os.getenv("CASE_FINDER_URL", "http://localhost:8001")
    SUMMARY_URL = os.getenv("SUMMARY_URL", "http://localhost:8002")
    CITATION_URL = os.getenv("CITATION_URL", "http://localhost:8003")
    PRECEDENT_URL = os.getenv("PRECEDENT_URL", "http://localhost:8004")
    JWT_SECRET = os.getenv("JWT_SECRET")
    ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
    CASE_TYPE_LABELS_URL = os.getenv("CASE_TYPE_LABELS_URL", "")
    TOPIC_LABELS_URL = os.getenv("TOPIC_LABELS_URL", "")
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "veritasai")
