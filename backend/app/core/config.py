from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # APP
    environment: str = "development"

    # LLM
    llm_model: str = "gpt-4o-mini"
    openai_api_key: SecretStr
    api_base_url: str = "https://api.openai.com/v1"

    # Request Settings
    timeout: float = 30.0
    retry_count: int = 3

    # External APIs
    courtlistener_api_key: SecretStr

    # Logging
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
