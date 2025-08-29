from dotenv import load_dotenv
import os

load_dotenv()


class Config:
    HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")
    COURTLISTENER_API_KEY = os.getenv("COURTLISTENER_API_KEY")
    CASE_FINDER_URL = os.getenv("CASE_FINDER_URL")
    SUMMARY_URL = os.getenv("SUMMARY_URL")
    CITATION_URL = os.getenv("CITATION_URL")
    JWT_SECRET = os.getenv("JWT_SECRET")
    ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
    COURTLISTENER_BASE_URL = os.getenv(
        "COURTLISTENER_BASE_URL", "https://www.courtlistener.com/api/rest/v3/")
