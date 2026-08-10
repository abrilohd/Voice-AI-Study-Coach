"""Unit tests for document routes and RAG chat endpoint."""

import io
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import UploadFile
from starlette.requests import Request

from app.models.document import Document, DocumentStatus
from app.schemas.document import RetrievedChunk
from app.services.exceptions import (
    DocumentNotFoundError,
    DocumentProcessingError,
)


def create_mock_request():
    """Create a mock Starlette Request for rate limiting."""
    # Create a mock app with state
    mock_app = MagicMock()
    mock_app.state.limiter = AsyncMock()
    
    # Create a minimal mock scope for Starlette Request
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/test",
        "query_string": b"",
        "headers": [(b"user-agent", b"test")],
        "client": ("127.0.0.1", 50000),
        "server": ("testserver", 80),
        "app": mock_app,  # Add app to scope
    }
    
    # Create mock receive and send
    async def receive():
        return {"type": "http.request", "body": b""}
    
    async def send(message):
        pass
    
    return Request(scope, receive, send)


@pytest.fixture
def mock_rag_service():
    """Mock RAG service with AsyncMock."""
    service = AsyncMock(spec=[
        "ingest_document",
        "list_documents",
        "get_document",
        "delete_document",
        "retrieve_chunks",
        "build_rag_context",
    ])
    
    # Make async methods actually awaitable by wrapping returns in coroutines
    async def async_return(value):
        return value
    
    # Set side_effect to wrap return values (split for line length)
    service.ingest_document.side_effect = (
        lambda *args, **kwargs: async_return(service.ingest_document.return_value)
    )
    service.list_documents.side_effect = (
        lambda *args, **kwargs: async_return(service.list_documents.return_value)
    )
    service.get_document.side_effect = (
        lambda *args, **kwargs: async_return(service.get_document.return_value)
    )
    service.delete_document.side_effect = (
        lambda *args, **kwargs: async_return(service.delete_document.return_value)
    )
    service.retrieve_chunks.side_effect = (
        lambda *args, **kwargs: async_return(service.retrieve_chunks.return_value)
    )
    service.build_rag_context.side_effect = (
        lambda *args, **kwargs: async_return(service.build_rag_context.return_value)
    )
    
    return service


@pytest.fixture
def fake_document():
    """Helper to create fake Document objects."""

    def _create(
        document_id=None,
        user_id=None,
        title="Test Document",
        filename="test.pdf",
        status=DocumentStatus.PENDING,
        chunk_count=0,
    ):
        return Document(
            id=document_id or uuid4(),
            user_id=user_id or uuid4(),
            title=title,
            description="Test description",
            filename=filename,
            file_size_bytes=1024,
            chunk_count=chunk_count,
            status=status,
            created_at=datetime.now(timezone.utc),  # Add required timestamp
        )

    return _create


# ==================== UPLOAD TESTS ====================


@pytest.mark.asyncio
async def test_upload_document_success(mock_rag_service, fake_document):
    """Test successful document upload returns pending status."""
    from app.api.v1.routers.documents import upload_document
    from app.models.user import User

    # Mock user
    user = User(id=uuid4(), email="test@example.com", hashed_password="hash")

    # Mock successful ingestion
    doc = fake_document(user_id=user.id, status=DocumentStatus.PENDING)
    mock_rag_service.ingest_document.return_value = doc

    # Create fake upload file
    file_content = b"Test PDF content"
    upload_file = UploadFile(
        filename="test.pdf",
        file=io.BytesIO(file_content),
    )

    # Mock request for rate limiting
    mock_request = create_mock_request()

    # Call endpoint
    response = await upload_document(
        request=mock_request,
        file=upload_file,
        title="Test Document",
        description="Test description",
        current_user=user,
        rag_service=mock_rag_service,
    )

    # Assert response
    assert response.title == "Test Document"
    assert response.status == "pending"
    assert response.user_id == user.id

    # Verify service was called
    mock_rag_service.ingest_document.assert_called_once()
    call_args = mock_rag_service.ingest_document.call_args
    assert call_args.kwargs["user_id"] == user.id
    assert call_args.kwargs["title"] == "Test Document"
    assert call_args.kwargs["filename"] == "test.pdf"


@pytest.mark.asyncio
async def test_upload_invalid_extension():
    """Test upload with invalid file extension returns 422."""
    from fastapi import HTTPException

    from app.api.v1.routers.documents import upload_document
    from app.models.user import User

    user = User(id=uuid4(), email="test@example.com", hashed_password="hash")
    mock_rag_service = AsyncMock()
    mock_request = create_mock_request()

    # Create file with invalid extension
    upload_file = UploadFile(
        filename="malware.exe",
        file=io.BytesIO(b"executable"),
    )

    # Should raise 422
    with pytest.raises(HTTPException) as exc_info:
        await upload_document(
            request=mock_request,
            file=upload_file,
            title="Test",
            description=None,
            current_user=user,
            rag_service=mock_rag_service,
        )

    assert exc_info.value.status_code == 422
    assert "not supported" in exc_info.value.detail


@pytest.mark.asyncio
async def test_upload_exceeds_size_limit():
    """Test upload exceeding 10MB returns 413."""
    from fastapi import HTTPException

    from app.api.v1.routers.documents import upload_document
    from app.models.user import User

    user = User(id=uuid4(), email="test@example.com", hashed_password="hash")
    mock_rag_service = AsyncMock()
    mock_request = create_mock_request()

    # Create file larger than 10MB
    large_content = b"x" * (11 * 1024 * 1024)  # 11MB
    upload_file = UploadFile(
        filename="large.pdf",
        file=io.BytesIO(large_content),
    )

    # Should raise 413
    with pytest.raises(HTTPException) as exc_info:
        await upload_document(
            request=mock_request,
            file=upload_file,
            title="Large File",
            description=None,
            current_user=user,
            rag_service=mock_rag_service,
        )

    assert exc_info.value.status_code == 413
    assert "exceeds maximum" in exc_info.value.detail


@pytest.mark.asyncio
async def test_upload_processing_error():
    """Test document processing error returns 422."""
    from fastapi import HTTPException

    from app.api.v1.routers.documents import upload_document
    from app.models.user import User

    user = User(id=uuid4(), email="test@example.com", hashed_password="hash")
    mock_rag_service = AsyncMock()
    mock_request = create_mock_request()

    # Mock processing error
    mock_rag_service.ingest_document.side_effect = DocumentProcessingError(
        "Failed to extract text"
    )

    upload_file = UploadFile(
        filename="corrupt.pdf",
        file=io.BytesIO(b"corrupt"),
    )

    # Should raise 422
    with pytest.raises(HTTPException) as exc_info:
        await upload_document(
            request=mock_request,
            file=upload_file,
            title="Corrupt File",
            description=None,
            current_user=user,
            rag_service=mock_rag_service,
        )

    assert exc_info.value.status_code == 422
    assert "Failed to extract text" in exc_info.value.detail


# ==================== LIST TESTS ====================


@pytest.mark.asyncio
async def test_list_documents_returns_user_scope(mock_rag_service, fake_document):
    """Test list documents returns only user's documents."""
    from app.api.v1.routers.documents import list_documents
    from app.models.user import User

    user = User(id=uuid4(), email="test@example.com", hashed_password="hash")
    mock_request = create_mock_request()

    # Mock list response
    doc1 = fake_document(user_id=user.id, title="Doc 1")
    doc2 = fake_document(user_id=user.id, title="Doc 2")
    mock_rag_service.list_documents.return_value = [doc1, doc2]

    # Call endpoint
    response = await list_documents(
        request=mock_request,
        limit=20,
        offset=0,
        current_user=user,
        rag_service=mock_rag_service,
    )

    # Assert response
    assert len(response) == 2
    assert response[0].title == "Doc 1"
    assert response[1].title == "Doc 2"

    # Verify service called with correct user_id
    mock_rag_service.list_documents.assert_called_once_with(
        user_id=user.id,
        limit=20,
        offset=0,
    )


# ==================== GET TESTS ====================


@pytest.mark.asyncio
async def test_get_document_success(mock_rag_service, fake_document):
    """Test get single document returns document."""
    from app.api.v1.routers.documents import get_document
    from app.models.user import User

    user = User(id=uuid4(), email="test@example.com", hashed_password="hash")
    doc_id = uuid4()
    mock_request = create_mock_request()

    # Mock get response
    doc = fake_document(document_id=doc_id, user_id=user.id)
    mock_rag_service.get_document.return_value = doc

    # Call endpoint
    response = await get_document(
        request=mock_request,
        document_id=str(doc_id),
        current_user=user,
        rag_service=mock_rag_service,
    )

    # Assert response
    assert response.id == doc_id
    assert response.user_id == user.id

    # Verify service called
    mock_rag_service.get_document.assert_called_once_with(
        document_id=doc_id,
        user_id=user.id,
    )


@pytest.mark.asyncio
async def test_get_document_not_found():
    """Test get document raises 404 when not found."""
    from fastapi import HTTPException

    from app.api.v1.routers.documents import get_document
    from app.models.user import User

    user = User(id=uuid4(), email="test@example.com", hashed_password="hash")
    doc_id = uuid4()
    mock_rag_service = AsyncMock()
    mock_request = create_mock_request()

    # Mock not found
    mock_rag_service.get_document.side_effect = DocumentNotFoundError(doc_id)

    # Should raise 404
    with pytest.raises(HTTPException) as exc_info:
        await get_document(
            request=mock_request,
            document_id=str(doc_id),
            current_user=user,
            rag_service=mock_rag_service,
        )

    assert exc_info.value.status_code == 404
    assert "not found" in exc_info.value.detail


# ==================== DELETE TESTS ====================


@pytest.mark.asyncio
async def test_delete_document_success(mock_rag_service):
    """Test delete document returns 204."""
    from app.api.v1.routers.documents import delete_document
    from app.models.user import User

    user = User(id=uuid4(), email="test@example.com", hashed_password="hash")
    doc_id = uuid4()
    mock_request = create_mock_request()

    # Mock successful delete
    mock_rag_service.delete_document.return_value = None

    # Call endpoint
    response = await delete_document(
        request=mock_request,
        document_id=str(doc_id),
        current_user=user,
        rag_service=mock_rag_service,
    )

    # Assert no content
    assert response is None

    # Verify service called
    mock_rag_service.delete_document.assert_called_once_with(
        document_id=doc_id,
        user_id=user.id,
    )


@pytest.mark.asyncio
async def test_delete_document_not_found():
    """Test delete document raises 404 when not found."""
    from fastapi import HTTPException

    from app.api.v1.routers.documents import delete_document
    from app.models.user import User

    user = User(id=uuid4(), email="test@example.com", hashed_password="hash")
    doc_id = uuid4()
    mock_rag_service = AsyncMock()
    mock_request = create_mock_request()

    # Mock not found
    mock_rag_service.delete_document.side_effect = DocumentNotFoundError(doc_id)

    # Should raise 404
    with pytest.raises(HTTPException) as exc_info:
        await delete_document(
            request=mock_request,
            document_id=str(doc_id),
            current_user=user,
            rag_service=mock_rag_service,
        )

    assert exc_info.value.status_code == 404
    assert "not found" in exc_info.value.detail


# ==================== RAG STREAM TESTS ====================


@pytest.mark.asyncio
async def test_rag_stream_with_chunks(mock_rag_service):
    """Test RAG stream with retrieved chunks includes sources in done event."""
    from app.api.v1.routers.chat_rag import stream_rag_chat
    from app.models.user import User
    from app.schemas.chat import MessageCreate
    from app.schemas.document import RAGChatRequest

    user = User(id=uuid4(), email="test@example.com", hashed_password="hash")
    mock_request = create_mock_request()
    mock_chat_service = AsyncMock()

    # Mock retrieved chunks
    chunk1 = RetrievedChunk(
        chunk_id=uuid4(),
        document_id=uuid4(),
        document_title="Test Doc",
        content="Test content",
        similarity_score=0.85,
        chunk_index=0,
    )
    chunk2 = RetrievedChunk(
        chunk_id=uuid4(),
        document_id=uuid4(),
        document_title="Another Doc",
        content="More content",
        similarity_score=0.75,
        chunk_index=1,
    )
    mock_rag_service.retrieve_chunks.return_value = [chunk1, chunk2]
    mock_rag_service.build_rag_context.return_value = "RAG context string"

    # Mock LLM router to yield tokens and usage
    async def mock_stream(*args, **kwargs):
        yield {"type": "text", "content": "Hello"}
        yield {"type": "text", "content": " world"}
        yield {"type": "usage", "input_tokens": 100, "output_tokens": 20}

    # Patch llm_router.stream
    with patch("app.api.v1.routers.chat_rag.llm_router.stream", side_effect=mock_stream):
        # Create request
        chat_request = RAGChatRequest(
            messages=[
                MessageCreate(role="user", content="Tell me about calculus"),
            ],
            topic="Math",
            use_rag=True,
            document_ids=None,
        )

        # Call endpoint
        response = await stream_rag_chat(
            request=mock_request,
            chat_request=chat_request,
            current_user=user,
            chat_service=mock_chat_service,
            rag_service=mock_rag_service,
        )

        # Read stream
        chunks = []
        async for chunk in response.body_iterator:
            # StreamingResponse body_iterator yields strings, not bytes
            chunks.append(chunk if isinstance(chunk, str) else chunk.decode("utf-8"))

        # Join all chunks
        full_response = "".join(chunks)

        # Assert text chunks were sent
        assert "Hello" in full_response
        assert "world" in full_response

        # Assert done event includes sources
        assert '"type": "done"' in full_response
        assert '"sources"' in full_response
        assert '"document_title": "Test Doc"' in full_response
        assert '"similarity_score": 0.85' in full_response


@pytest.mark.asyncio
async def test_rag_stream_no_chunks_fallback(mock_rag_service):
    """Test RAG stream with no chunks still streams normally."""
    from app.api.v1.routers.chat_rag import stream_rag_chat
    from app.models.user import User
    from app.schemas.chat import MessageCreate
    from app.schemas.document import RAGChatRequest

    user = User(id=uuid4(), email="test@example.com", hashed_password="hash")
    mock_request = create_mock_request()
    mock_chat_service = AsyncMock()

    # Mock empty retrieval
    mock_rag_service.retrieve_chunks.return_value = []

    # Mock LLM router
    async def mock_stream(*args, **kwargs):
        yield {"type": "text", "content": "No context found"}
        yield {"type": "usage", "input_tokens": 50, "output_tokens": 10}

    with patch("app.api.v1.routers.chat_rag.llm_router.stream", side_effect=mock_stream):
        chat_request = RAGChatRequest(
            messages=[
                MessageCreate(role="user", content="Random question"),
            ],
            topic=None,
            use_rag=True,
            document_ids=None,
        )

        # Call endpoint
        response = await stream_rag_chat(
            request=mock_request,
            chat_request=chat_request,
            current_user=user,
            chat_service=mock_chat_service,
            rag_service=mock_rag_service,
        )

        # Read stream
        chunks = []
        async for chunk in response.body_iterator:
            # StreamingResponse body_iterator yields strings, not bytes
            chunks.append(chunk if isinstance(chunk, str) else chunk.decode("utf-8"))

        full_response = "".join(chunks)

        # Assert stream still works
        assert "No context found" in full_response
        assert '"type": "done"' in full_response

        # Assert sources is empty array
        assert '"sources": []' in full_response
