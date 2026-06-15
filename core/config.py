from pydantic_settings import BaseSettings, SettingConfigDict 

class Settings(BaseSettings):
    model_config = SettingConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    APP_NAME:str = "VeritasAI"
    DEBUG:bool = False
    Environment:str = "production"

    LLM_MODEL:str = "gpt-4o-mini"
    TEMPERATURE:float = 0.4
    OPENAI_API_KEY:str
    API_BASE_URL:str = "https://api.openai.com/v1"

    MONGO_URI:str
    DATABASE_NAME:str = "veritas_ai"

    GOOGLE_CLIENT_ID:str
    GOOGLE_CLIENT_SECRET:str
    JWT_SECRET:str
    JWT_ALGORITHM:str = "HS256"
    JWT_EXPIRY_HOURS:int = 24
    SESSION_SECRET_KEY:str
    ENCRYPTION_KEY:str

    COURTLISTENER_API_KEY:str
    ALLOWED_ORIGINS:str = "http://localhost:3000"
    LOG_LEVEL:str = "INFO"
    LOG_DIR:str = "./logs"





