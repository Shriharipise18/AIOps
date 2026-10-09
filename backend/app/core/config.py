"""
Core configuration module.
Loads all settings from environment variables using Pydantic Settings.
"""
from pydantic_settings import BaseSettings
from pydantic import SecretStr
from typing import Literal
from functools import lru_cache


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "AI DevOps Assistant"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LLM_PROVIDER: Literal["groq", "openai"] = "groq"
    GROQ_API_KEY: SecretStr | None = None
    GROQ_MODEL: str = "openai/gpt-oss-120b"
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"
    OPENAI_API_KEY: SecretStr | None = None

    # API
    API_PREFIX: str = "/api/v1"

    # MongoDB
    MONGODB_URL: SecretStr = SecretStr("mongodb://localhost:27017")
    MONGODB_DATABASE: str = "devops_assistant"

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""
    REDIS_ENABLED: bool = False

    # CORS
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://frontend:5173",
    ]

    @property
    def REDIS_URL(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()


settings = get_settings()
