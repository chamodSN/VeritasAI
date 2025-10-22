import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai_api")
    MODEL_NAME = os.getenv("LLM_MODEL", "gpt-4o-mini")
    TEMPERATURE = float(os.getenv("TEMPERATURE", 0.4))
    API_KEY = os.getenv("OPENAI_API_KEY")
    API_BASE_URL = os.getenv("API_BASE_URL", "https://api.openai.com/v1")
    MONGO_URI = os.getenv("MONGO_URI")
    DATABASE_NAME = os.getenv("DATABASE_NAME", "legal_ai")
    VECTOR_STORE = os.getenv("EMBEDDINGS_PATH", "./data/embeddings/")
    LOG_DIR = os.getenv("LOG_DIR", "./logs/")
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
    SESSION_SECRET_KEY = os.getenv("SESSION_SECRET_KEY")
    JWT_SECRET = os.getenv("JWT_SECRET")
    ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
    DATA_PATH = os.getenv("DATA_PATH", "./data/corpus/")
    COURTLISTENER_API_KEY = os.getenv("COURTLISTENER_API_KEY")
