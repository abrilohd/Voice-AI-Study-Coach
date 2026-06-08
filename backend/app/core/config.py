"""Application configuration using pydantic-settings."""

from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    # Application
    app_name: str = "Voice AI Study Coach"
    app_version: str = "0.1.0"
    debug: bool = False

    # Database
    database_url: str = ""

    # Security
    secret_key: str = ""
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # LLM API Keys
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    gemini_api_key: str = ""

    # LLM Configuration
    primary_llm: Literal["claude", "openai", "gemini"] = "claude"
    fallback_llm: Literal["claude", "openai", "gemini"] = "openai"

    # CORS
    cors_origins: list[str] = ["http://localhost:5173"]

    @field_validator("database_url", mode="after")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Validate that database_url uses asyncpg driver when not empty."""
        if v and not v.startswith("postgresql+asyncpg://"):
            raise ValueError(
                "database_url must start with 'postgresql+asyncpg://' for async support"
            )
        return v


settings = Settings()
