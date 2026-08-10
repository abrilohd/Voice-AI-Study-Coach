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
    dummy_hash: str = (
        "$argon2id$v=19$m=65536,t=3,p=4$dummy$dummydummydummydummydummydummydummydummydummydummy"
    )
    environment: Literal["development", "production"] = "development"

    # LLM API Keys
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    gemini_api_key: str = ""

    # LLM Configuration
    primary_llm: Literal["claude", "openai", "gemini"] = "claude"
    fallback_llm: Literal["claude", "openai", "gemini"] = "openai"

    # Model names
    claude_model: str = "claude-3-5-sonnet-20241022"
    openai_model: str = "gpt-4o"
    gemini_model: str = "gemini-2.0-flash-exp"

    # Generation settings
    max_response_tokens: int = 4096
    prompt_cache_min_tokens: int = 1024  # Anthropic minimum for caching

    # CORS
    cors_origins: list[str] = ["http://localhost:5173"]

    # RAG Configuration
    voyage_api_key: str = ""
    embedding_model: str = "voyage-3"
    embedding_dimensions: int = 1536
    max_rag_chunks: int = 5
    rag_similarity_threshold: float = 0.70

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
