"""Document repository for database operations."""

from typing import Any
from uuid import UUID

from sqlalchemy import delete, insert, select, update
from sqlalchemy.engine import Result
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentChunk, DocumentStatus


class DocumentRepository:
    """Repository for Document and DocumentChunk database operations.

    NOTE: This repository NEVER calls commit() or rollback().
    Session lifecycle management belongs to the caller (service layer).
    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            db: Async SQLAlchemy session
        """
        self.db = db

    async def create_document(
        self,
        user_id: UUID,
        title: str,
        description: str | None,
        filename: str,
        file_size_bytes: int,
    ) -> Document:
        """Create a new document.

        Uses flush() not commit() - caller is responsible for commit.

        Args:
            user_id: Owner user ID
            title: Document title
            description: Optional document description
            filename: Original filename
            file_size_bytes: File size in bytes

        Returns:
            Created Document object
        """
        document = Document(
            user_id=user_id,
            title=title,
            description=description,
            filename=filename,
            file_size_bytes=file_size_bytes,
        )
        self.db.add(document)
        await self.db.flush()
        await self.db.refresh(document)
        return document

    async def get_document_by_id(
        self,
        document_id: UUID,
        user_id: UUID,
    ) -> Document | None:
        """Get document by ID, scoped to user.

        Always enforces ownership - no cross-user reads.

        Args:
            document_id: Document ID
            user_id: Owner user ID (enforces ownership)

        Returns:
            Document object or None if not found
        """
        result = await self.db.execute(
            select(Document).where(
                Document.id == document_id,
                Document.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_documents(
        self,
        user_id: UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Document]:
        """List documents for a user with pagination.

        Args:
            user_id: Owner user ID
            limit: Maximum number of documents to return
            offset: Number of documents to skip

        Returns:
            List of Document objects
        """
        result = await self.db.execute(
            select(Document)
            .where(Document.user_id == user_id)
            .order_by(Document.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def update_document_status(
        self,
        document_id: UUID,
        status: DocumentStatus,
        chunk_count: int | None = None,
    ) -> None:
        """Update document processing status.

        Uses flush() not commit() - caller is responsible for commit.

        Args:
            document_id: Document ID
            status: New processing status
            chunk_count: Optional chunk count (updates if provided)
        """
        values: dict[str, Any] = {"status": status}
        if chunk_count is not None:
            values["chunk_count"] = chunk_count

        await self.db.execute(
            update(Document).where(Document.id == document_id).values(**values)
        )
        await self.db.flush()

    async def delete_document(
        self,
        document_id: UUID,
        user_id: UUID,
    ) -> bool:
        """Delete document by ID, scoped to user.

        Enforces ownership before delete - no cross-user deletes.

        Args:
            document_id: Document ID
            user_id: Owner user ID (enforces ownership)

        Returns:
            True if document was deleted, False if not found
        """
        result: Result[Any] = await self.db.execute(
            delete(Document).where(
                Document.id == document_id,
                Document.user_id == user_id,
            )
        )
        await self.db.flush()
        # Result from DML operations has rowcount attribute at runtime
        # but type stubs don't reflect this - safe to access
        return result.rowcount > 0  # type: ignore[attr-defined,no-any-return]

    async def create_chunks_bulk(
        self,
        chunks: list[dict[str, Any]],
    ) -> None:
        """Create multiple document chunks in bulk.

        Uses bulk insert for performance (10-100x faster than loop).
        Uses flush() not commit() - caller is responsible for commit.

        Args:
            chunks: List of chunk dicts with keys:
                document_id, chunk_index, content, token_count, embedding
        """
        if not chunks:
            return

        await self.db.execute(insert(DocumentChunk), chunks)
        await self.db.flush()

    async def similarity_search(
        self,
        user_id: UUID,
        query_embedding: list[float],
        document_ids: list[UUID] | None,
        limit: int = 5,
        similarity_threshold: float = 0.7,
    ) -> list[tuple[DocumentChunk, Document, float]]:
        """Search for similar document chunks using vector similarity.

        Uses pgvector cosine distance for similarity search.
        Returns chunks with similarity score >= threshold.

        Args:
            user_id: Owner user ID (enforces ownership)
            query_embedding: Query vector embedding
            document_ids: Optional list of document IDs to search within
            limit: Maximum number of results
            similarity_threshold: Minimum similarity score (0-1)

        Returns:
            List of tuples (chunk, document, similarity_score)
        """
        # Compute cosine distance and similarity score
        distance = DocumentChunk.embedding.cosine_distance(query_embedding)
        similarity_score = 1 - distance

        # Build query with JOIN
        stmt = (
            select(DocumentChunk, Document, similarity_score.label("score"))
            .join(Document, DocumentChunk.document_id == Document.id)
            .where(
                Document.user_id == user_id,
                similarity_score >= similarity_threshold,
            )
            .order_by(distance.asc())
            .limit(limit)
        )

        # Filter by document IDs if provided
        if document_ids is not None:
            stmt = stmt.where(Document.id.in_(document_ids))

        result = await self.db.execute(stmt)
        rows = result.all()

        return [(row[0], row[1], float(row[2])) for row in rows]
