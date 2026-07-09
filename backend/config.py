"""Application settings loaded from environment variables (.env).

Owner: Ahmad
"""
from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    environment: str = "development"
    database_url: str = "postgresql://aura:aura@localhost:5432/aura"
    redis_url: str = "redis://localhost:6379/0"
    openai_api_key: str = ""
    secret_key: str = "change-me"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
