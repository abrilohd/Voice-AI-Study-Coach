"""Chat schemas for conversation and message requests/responses."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ConversationCreate(BaseModel):
    """Schema for creating a new conversation."""

    title: str = Field(default="New conversation", max_length=200)
    topic: str | None = Field(default=None, max_length=100)
    llm_provider: Literal["claude", "openai", "gemini"] = "claude"
    is_voice: bool = False


class MessageCreate(BaseModel):
    """Schema for creating a message within a conversation."""

    content: str = Field(min_length=1, max_length=32000)
    role: Literal["user", "assistant", "system"] = "user"


class ChatRequest(BaseModel):
    """Schema for chat API request with messages and context."""

    messages: list[MessageCreate] = Field(min_length=1, max_length=50)
    topic: str | None = None
    provider: Literal["claude", "openai", "gemini"] | None = None
    conversation_id: UUID | None = None  # None = create new conversation
    use_prompt_cache: bool = True  # Anthropic prompt caching flag


class MessageResponse(BaseModel):
    """Schema for message response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: str
    content: str
    token_count: int
    created_at: datetime


class ConversationResponse(BaseModel):
    """Schema for conversation response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    topic: str | None
    llm_provider: str
    is_voice: bool
    message_count: int = 0
    created_at: datetime
    updated_at: datetime
