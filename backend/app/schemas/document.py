"""Document schemas for RAG pipeline request/response validation."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.chat import MessageCreate


class DocumentUpload(BaseModel):
    """Schema for document upload metadata (file content is multipart/form-data)."""

    title: str = Field(
        description="Human-readable label for the document",
        examples=["Calculus Chapter 3"],
        min_length=1,
        max_length=200,
    )
    description: str | None = Field(
        default=None,
        description="Optional description of document content",
        examples=["Derivatives and integrals from Stewart Calculus"],
        max_length=1000,
    )


class DocumentResponse(BaseModel):
    """Response schema for document metadata."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(
        description="Unique document identifier",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    user_id: UUID = Field(
        description="ID of user who uploaded the document",
        examples=["660e8400-e29b-41d4-a716-446655440001"],
    )
    title: str = Field(
        description="Document title",
        examples=["Calculus Chapter 3"],
    )
    description: str | None = Field(
        description="Document description",
        examples=["Derivatives and integrals from Stewart Calculus"],
    )
    filename: str = Field(
        description="Original filename from upload",
        examples=["calculus_ch3.pdf"],
    )
    file_size_bytes: int = Field(
        description="File size in bytes",
        examples=[2048576],
    )
    chunk_count: int = Field(
        description="Number of chunks created (0 until processing complete)",
        examples=[42],
    )
    status: Literal["pending", "processing", "ready", "failed"] = Field(
        description="Document processing status",
        examples=["ready"],
    )
    created_at: datetime = Field(
        description="Timestamp when document was uploaded",
        examples=["2026-06-10T12:00:00Z"],
    )


class ChunkResponse(BaseModel):
    """Response schema for document chunk metadata (no embedding vector)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(
        description="Unique chunk identifier",
        examples=["770e8400-e29b-41d4-a716-446655440002"],
    )
    document_id: UUID = Field(
        description="Parent document ID",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    chunk_index: int = Field(
        description="Zero-based index of chunk in document",
        examples=[0],
    )
    content: str = Field(
        description="Text content of the chunk",
        examples=["The derivative of a function f(x) is defined as..."],
    )
    token_count: int = Field(
        description="Token count from tiktoken (never an estimate)",
        examples=[256],
    )


class RAGChatRequest(BaseModel):
    """Schema for RAG-augmented chat request (extends ChatRequest)."""

    messages: list[MessageCreate] = Field(
        description="List of messages in the conversation",
        min_length=1,
        max_length=50,
    )
    topic: str | None = Field(
        default=None,
        description="Optional topic for the conversation",
        examples=["Calculus derivatives"],
        max_length=100,
    )
    use_rag: bool = Field(
        default=True,
        description="Whether to use RAG retrieval for this request",
        examples=[True],
    )
    document_ids: list[UUID] | None = Field(
        default=None,
        description="Specific document IDs to search (None = search all user documents)",
        examples=[["550e8400-e29b-41d4-a716-446655440000"]],
    )


class RetrievedChunk(BaseModel):
    """
    Schema for retrieved chunk with similarity score.
    
    Internal use only — never exposes raw embeddings.
    """

    chunk_id: UUID = Field(
        description="Unique chunk identifier",
        examples=["770e8400-e29b-41d4-a716-446655440002"],
    )
    document_id: UUID = Field(
        description="Parent document ID",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    document_title: str = Field(
        description="Title of the source document",
        examples=["Calculus Chapter 3"],
    )
    content: str = Field(
        description="Text content of the chunk",
        examples=["The derivative of a function f(x) is defined as..."],
    )
    similarity_score: float = Field(
        description="Cosine similarity score (0.0–1.0)",
        examples=[0.87],
        ge=0.0,
        le=1.0,
    )
    chunk_index: int = Field(
        description="Zero-based index of chunk in document",
        examples=[0],
    )
