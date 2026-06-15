from pydantic_settings import BaseSettings, SettingConfigDict 
from pydantic import field_validator
from typing import List

class Settings(BaseSettings):
    model_config = SettingConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Application
    APP_NAME:str = "VeritasAI"
    DEBUG:bool = False
    Environment:str = "production"

    #LLM
    LLM_MODEL:str = "gpt-4o-mini"
    TEMPERATURE:float = 0.4
    OPENAI_API_KEY:str
    API_BASE_URL:str = "https://api.openai.com/v1"

    #DB
    MONGO_URI:str
    DATABASE_NAME:str = "veritas_ai"

    # Authentication
    GOOGLE_CLIENT_ID:str
    GOOGLE_CLIENT_SECRET:str
    JWT_SECRET:str
    JWT_ALGORITHM:str = "HS256"
    JWT_EXPIRY_HOURS:int = 24
    SESSION_SECRET_KEY:str

    #Security
    ENCRYPTION_KEY:str

    #External APIs
    COURTLISTENER_API_KEY:str

    #CORS
    ALLOWED_ORIGINS:str = "http://localhost:3000"

    #Logging
    LOG_LEVEL:str = "INFO"
    LOG_DIR:str = "./logs"

    @field_validator("TEMPERATURE")
    @classmethod
    def temperature_range(cls, v:float) -> float:
        if not (0.0 <= v <= 2.0):
            raise ValueError("TEMPERATURE must be between 0.0 and 2.0")
        return v
    
    @field_validator("ENCRYPTION_KEY")
    @classmethod
    def validate_encryption_key(cls, v:str) -> str:
        import base64
        try:
            base64.urlsafe_b64decode(v.encode())
            if len(v) != 32:
                raise ValueError("Encryption key must decode to exactly 32 bytes")
        except Exception as exc:
            raise ValueError(
                "ENCRYPTION_KEY must be a valid Fernet key. "
                ) from exc
        return v
    
    @property
    def allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]
    
    @property
    def is_development(self) -> bool:
        return self.Environment.lower() == "development"

settings = Settings()




