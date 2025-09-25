import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")
    COURTLISTENER_API_KEY = os.getenv("COURTLISTENER_API_KEY")
    COURTLISTENER_BASE_URL = os.getenv(
        "COURTLISTENER_BASE_URL", "https://www.courtlistener.com/api/rest/v4/")
    CASE_FINDER_URL = os.getenv("CASE_FINDER_URL", "http://localhost:8001")
    QUERY_UNDERSTANDING_URL: str = "http://localhost:8001"
    SUMMARY_URL = os.getenv("SUMMARY_URL", "http://localhost:8002")
    CITATION_URL = os.getenv("CITATION_URL", "http://localhost:8003")
    PRECEDENT_URL = os.getenv("PRECEDENT_URL", "http://localhost:8004")
    JWT_SECRET = os.getenv("JWT_SECRET")
    ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
    CASE_TYPE_LABELS_URL = os.getenv(
        "CASE_TYPE_LABELS_URL", "http://localhost:5000/case_types")
    TOPIC_LABELS_URL = os.getenv(
        "TOPIC_LABELS_URL", "http://localhost:5000/topics")

    # Responsible AI Configuration
    # Reduced for performance
    MAX_QUERY_LENGTH = int(os.getenv("MAX_QUERY_LENGTH", "500"))
    # Reduced for performance
    MAX_RESULTS_PER_QUERY = int(os.getenv("MAX_RESULTS_PER_QUERY", "5"))
    # Increased for stricter filtering
    MIN_CONFIDENCE_THRESHOLD = float(
        os.getenv("MIN_CONFIDENCE_THRESHOLD", "0.4"))
    ENABLE_BIAS_DETECTION = os.getenv(
        "ENABLE_BIAS_DETECTION", "true").lower() == "true"
    SIMILARITY_THRESHOLD = 0.5  # Added for fixes
