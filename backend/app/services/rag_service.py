"""RAG service for document ingestion, chunking, embedding, and retrieval."""

import io
from typing import Any
from uuid import UUID

import structlog
import tiktoken
import voyageai
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.document import Document, DocumentStatus
from app.repositories.document_repository import DocumentRepository
from app.schemas.document import RetrievedChunk
from app.services.exceptions import (
    DocumentNotFoundError,
    DocumentProcessingError,
    EmbeddingError,
)

log = structlog.get_logger()


class RAGService:
    """Service for RAG pipeline operations.

    Handles document ingestion, text extraction, chunking, embedding generation,
    and semantic retrieval with proper transaction management.

    Constants:
        CHUNK_SIZE_TOKENS: Target tokens per chunk
        CHUNK_OVERLAP_TOKENS: Overlap prevents context loss at boundaries
        EMBEDDING_MODEL: Voyage AI model for embeddings
        EMBEDDING_BATCH_SIZE: Voyage API limit per request
        MIN_SIMILARITY: Below this, chunks are noise not signal
        MAX_CHUNKS_IN_CONTEXT: Inject at most 5 chunks for context budget
        MIN_CHUNK_TOKENS: Strip chunks shorter than this (headers/footers)
    """

    CHUNK_SIZE_TOKENS = 512
    CHUNK_OVERLAP_TOKENS = 64
    EMBEDDING_MODEL = "voyage-3"
    EMBEDDING_BATCH_SIZE = 128
    MIN_SIMILARITY = 0.70
    MAX_CHUNKS_IN_CONTEXT = 5
    MIN_CHUNK_TOKENS = 50

    def __init__(self, document_repo: DocumentRepository, db: AsyncSession) -> None:
        """Initialize RAG service.

        Args:
            document_repo: Repository for document operations
            db: Database session for transaction management
        """
        self.document_repo = document_repo
        self.db = db
        self.voyage_client = voyageai.Client(api_key=settings.voyage_api_key)  # type: ignore[attr-defined]
        self.encoding = tiktoken.get_encoding("cl100k_base")

    async def ingest_document(
        self,
        user_id: UUID,
        title: str,
        description: str | None,
        filename: str,
        file_content: bytes,
    ) -> Document:
        """Full ingestion pipeline from raw bytes to searchable chunks.

        Pipeline steps:
        1. Create Document row with status=pending, flush
        2. Extract text from bytes (PDF or plain text)
        3. Chunk text using recursive character splitter
        4. Generate embeddings in batches
        5. Bulk insert chunks
        6. Update Document status=ready with chunk count
        7. ONE db.commit()

        On any exception after step 1: updates status=failed, commits, re-raises.

        Args:
            user_id: Owner user ID
            title: Document title
            description: Optional document description
            filename: Original filename
            file_content: Raw file bytes (PDF or text)

        Returns:
            Document object with status=ready

        Raises:
            DocumentProcessingError: If extraction, chunking, or embedding fails
        """
        # Step 1: Create document with pending status
        document = await self.document_repo.create_document(
            user_id=user_id,
            title=title,
            description=description,
            filename=filename,
            file_size_bytes=len(file_content),
        )

        log.info(
            "rag.ingest.started",
            document_id=str(document.id),
            user_id=str(user_id),
            filename=filename,
            file_size=len(file_content),
        )

        try:
            # Step 2: Extract text
            log.info("rag.ingest.extracting_text", document_id=str(document.id))
            text = self._extract_text(file_content, filename)
            if not text or len(text.strip()) < 100:
                raise DocumentProcessingError("Document contains insufficient text content")

            # Step 3: Chunk text
            log.info(
                "rag.ingest.chunking",
                document_id=str(document.id),
                text_length=len(text),
            )
            chunks = self._chunk_text(text)
            if not chunks:
                raise DocumentProcessingError("No valid chunks created from document")

            log.info(
                "rag.ingest.chunks_created",
                document_id=str(document.id),
                chunk_count=len(chunks),
            )

            # Step 4: Generate embeddings
            log.info("rag.ingest.embedding", document_id=str(document.id))
            chunk_texts = [chunk["content"] for chunk in chunks]
            embeddings = await self._embed_chunks(chunk_texts)

            # Step 5: Bulk insert chunks
            log.info("rag.ingest.saving_chunks", document_id=str(document.id))
            chunk_dicts = [
                {
                    "document_id": document.id,
                    "chunk_index": chunk["chunk_index"],
                    "content": chunk["content"],
                    "token_count": chunk["token_count"],
                    "embedding": embeddings[i],
                }
                for i, chunk in enumerate(chunks)
            ]
            await self.document_repo.create_chunks_bulk(chunk_dicts)

            # Step 6: Update document status to ready
            await self.document_repo.update_document_status(
                document_id=document.id,
                status=DocumentStatus.READY,
                chunk_count=len(chunks),
            )

            # Step 7: Commit everything
            await self.db.commit()

            log.info(
                "rag.ingest.completed",
                document_id=str(document.id),
                chunk_count=len(chunks),
            )

            # Refresh document to get updated fields
            await self.db.refresh(document)
            return document

        except Exception as e:
            # Update status to failed and commit before re-raising
            log.error(
                "rag.ingest.failed",
                document_id=str(document.id),
                error=str(e),
                error_type=type(e).__name__,
            )

            await self.document_repo.update_document_status(
                document_id=document.id,
                status=DocumentStatus.FAILED,
            )
            await self.db.commit()

            # Re-raise as DocumentProcessingError if not already
            if isinstance(e, (DocumentProcessingError, EmbeddingError)):
                raise
            raise DocumentProcessingError(str(e)) from e

    def _extract_text(self, file_content: bytes, filename: str) -> str:
        """Extract text from PDF or plain text file.

        Args:
            file_content: Raw file bytes
            filename: Original filename for extension detection

        Returns:
            Extracted text content

        Raises:
            DocumentProcessingError: If extraction fails
        """
        try:
            if filename.lower().endswith(".pdf"):
                # Extract text from PDF
                pdf_file = io.BytesIO(file_content)
                reader = PdfReader(pdf_file)
                text_parts = []
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                return "\n\n".join(text_parts)
            else:
                # Assume plain text, try UTF-8 decoding
                return file_content.decode("utf-8")

        except Exception as e:
            raise DocumentProcessingError(f"Text extraction failed: {str(e)}") from e

    def _chunk_text(self, text: str) -> list[dict[str, Any]]:
        """Chunk text using recursive character splitter with token-based sizing.

        Args:
            text: Full document text

        Returns:
            List of chunk dicts with keys: content, chunk_index, token_count
        """

        def token_length(txt: str) -> int:
            """Token count function for text splitter."""
            return len(self.encoding.encode(txt))

        # Create splitter with token-based sizing
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.CHUNK_SIZE_TOKENS,
            chunk_overlap=self.CHUNK_OVERLAP_TOKENS,
            length_function=token_length,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

        # Split text into chunks
        text_chunks = splitter.split_text(text)

        # Build chunk metadata with actual token counts
        chunks = []
        for idx, content in enumerate(text_chunks):
            token_count = token_length(content)
            # Skip chunks that are too short (likely headers/footers)
            if token_count >= self.MIN_CHUNK_TOKENS:
                chunks.append(
                    {
                        "content": content.strip(),
                        "chunk_index": idx,
                        "token_count": token_count,
                    }
                )

        return chunks

    async def _embed_chunks(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for text chunks using Voyage AI.

        Processes in batches to respect API limits.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors (1536 floats each)

        Raises:
            EmbeddingError: If API call fails or dimension mismatch
        """
        try:
            all_embeddings: list[list[float]] = []

            # Process in batches
            for i in range(0, len(texts), self.EMBEDDING_BATCH_SIZE):
                batch = texts[i : i + self.EMBEDDING_BATCH_SIZE]

                result = self.voyage_client.embed(
                    batch,
                    model=self.EMBEDDING_MODEL,
                    input_type="document",
                )

                # Embeddings are always list[float] from Voyage AI
                batch_embeddings: list[list[float]] = result.embeddings  # type: ignore[assignment]
                all_embeddings.extend(batch_embeddings)

            # Verify embedding dimensions - CRITICAL assertion
            if all_embeddings:
                actual_dims = len(all_embeddings[0])
                expected_dims = settings.embedding_dimensions
                assert actual_dims == expected_dims, (
                    f"Embedding dimension mismatch: expected {expected_dims}, got {actual_dims}"
                )

            return all_embeddings

        except Exception as e:
            if isinstance(e, EmbeddingError):
                raise
            raise EmbeddingError(str(e)) from e

    async def retrieve_chunks(
        self,
        user_id: UUID,
        query: str,
        document_ids: list[UUID] | None = None,
        limit: int | None = None,
    ) -> list[RetrievedChunk]:
        """Retrieve relevant chunks using semantic similarity search.

        Args:
            user_id: Owner user ID for scoping
            query: Query text to search for
            document_ids: Optional list of document IDs to filter by
            limit: Maximum chunks to return (defaults to MAX_CHUNKS_IN_CONTEXT)

        Returns:
            List of RetrievedChunk objects ordered by similarity

        Raises:
            EmbeddingError: If query embedding fails
        """
        if limit is None:
            limit = self.MAX_CHUNKS_IN_CONTEXT

        log.info(
            "rag.retrieve.started",
            user_id=str(user_id),
            query_length=len(query),
            document_ids=[str(d) for d in document_ids] if document_ids else None,
            limit=limit,
        )

        # Step 1: Embed query with input_type="query" for better retrieval
        try:
            result = self.voyage_client.embed(
                [query],
                model=self.EMBEDDING_MODEL,
                input_type="query",  # Different from document input type
            )
            # Query embedding is always list[float] from Voyage AI
            query_embedding: list[float] = result.embeddings[0]  # type: ignore[assignment]
        except Exception as e:
            raise EmbeddingError(f"Query embedding failed: {str(e)}") from e

        # Step 2: Search for similar chunks
        results = await self.document_repo.similarity_search(
            user_id=user_id,
            query_embedding=query_embedding,
            document_ids=document_ids,
            limit=limit,
            similarity_threshold=settings.rag_similarity_threshold,
        )

        log.info(
            "rag.retrieve.completed",
            user_id=str(user_id),
            results_count=len(results),
        )

        # Step 3: Map to schema objects
        retrieved = [
            RetrievedChunk(
                chunk_id=chunk.id,
                document_id=document.id,
                document_title=document.title,
                content=chunk.content,
                similarity_score=similarity,
                chunk_index=chunk.chunk_index,
            )
            for chunk, document, similarity in results
        ]

        return retrieved

    async def build_rag_context(
        self,
        retrieved: list[RetrievedChunk],
    ) -> str:
        """Format retrieved chunks for injection into system prompt.

        Args:
            retrieved: List of retrieved chunks with similarity scores

        Returns:
            Formatted context string for LLM prompt
        """
        if not retrieved:
            return ""

        # Build context with chunk references
        context_parts = ["## Relevant context from your documents\n"]

        for idx, chunk in enumerate(retrieved, 1):
            context_parts.append(
                f"[{idx}] From \"{chunk.document_title}\" "
                f"(relevance: {chunk.similarity_score:.0%})\n"
                f"{chunk.content}\n"
            )

        context_parts.append(
            "\n---\n"
            "Use this context to answer the user's question. If the context does not "
            "contain the answer, say so clearly rather than guessing.\n"
        )

        context_str = "\n".join(context_parts)

        # Log warning if context is very large - real token count from tiktoken
        token_count = len(self.encoding.encode(context_str))
        if token_count > 6000:
            log.warning(
                "rag.context.large",
                token_count=token_count,
                chunk_count=len(retrieved),
            )

        return context_str

    async def get_document(
        self,
        document_id: UUID,
        user_id: UUID,
    ) -> Document:
        """Get document with ownership verification.

        Args:
            document_id: Document ID
            user_id: Owner user ID

        Returns:
            Document object

        Raises:
            DocumentNotFoundError: If document doesn't exist or user doesn't own it
        """
        log.info(
            "rag.get_document",
            document_id=str(document_id),
            user_id=str(user_id),
        )

        document = await self.document_repo.get_document_by_id(
            document_id=document_id,
            user_id=user_id,
        )

        if document is None:
            raise DocumentNotFoundError(document_id)

        return document

    async def list_documents(
        self,
        user_id: UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Document]:
        """List user's documents with pagination.

        Args:
            user_id: Owner user ID
            limit: Maximum documents to return
            offset: Number of documents to skip

        Returns:
            List of Document objects
        """
        log.info(
            "rag.list_documents",
            user_id=str(user_id),
            limit=limit,
            offset=offset,
        )

        return await self.document_repo.list_documents(
            user_id=user_id,
            limit=limit,
            offset=offset,
        )

    async def delete_document(
        self,
        document_id: UUID,
        user_id: UUID,
    ) -> None:
        """Delete document with ownership verification.

        Commits the deletion to database.

        Args:
            document_id: Document ID
            user_id: Owner user ID

        Raises:
            DocumentNotFoundError: If document doesn't exist or user doesn't own it
        """
        log.info(
            "rag.delete_document.started",
            document_id=str(document_id),
            user_id=str(user_id),
        )

        deleted = await self.document_repo.delete_document(
            document_id=document_id,
            user_id=user_id,
        )

        if not deleted:
            raise DocumentNotFoundError(document_id)

        # ONE commit for delete operation
        await self.db.commit()

        log.info(
            "rag.delete_document.completed",
            document_id=str(document_id),
        )
