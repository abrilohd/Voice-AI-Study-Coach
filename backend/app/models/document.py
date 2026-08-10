"""Document and DocumentChunk models for RAG pipeline."""

import enum
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class DocumentStatus(enum.StrEnum):
    """Document processing status enum."""

    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class Document(Base):
    """Document model for uploaded study materials."""

    __tablename__ = "documents"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(String(1000))
    filename: Mapped[str] = mapped_column(String(255))
    file_size_bytes: Mapped[int] = mapped_column()
    chunk_count: Mapped[int] = mapped_column(default=0)
    status: Mapped[DocumentStatus] = mapped_column(default=DocumentStatus.PENDING)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="documents")
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class DocumentChunk(Base):
    """Document chunk model for RAG retrieval with vector embeddings."""

    __tablename__ = "document_chunks"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    document_id: Mapped[UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    chunk_index: Mapped[int] = mapped_column()
    content: Mapped[str] = mapped_column(Text)
    token_count: Mapped[int] = mapped_column()
    embedding: Mapped[Vector | None] = mapped_column(Vector(1536), nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    # Relationships
    document: Mapped["Document"] = relationship(back_populates="chunks")

    # IVFFlat index for approximate nearest-neighbor search
    # Note: ivfflat requires data to exist before it's efficient.
    # 'lists' parameter (100) is appropriate for <1M vectors; use hnsw at scale.
    __table_args__ = (
        Index(
            "ix_chunks_embedding",
            "embedding",
            postgresql_using="ivfflat",
            postgresql_with={"lists": 100},
        ),
    )
