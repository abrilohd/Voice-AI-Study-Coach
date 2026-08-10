"""Document routes for RAG pipeline: upload, list, get, delete."""

import logging

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)

from app.core.dependencies import (
    get_current_user,
    get_rag_service,
    limiter,
)
from app.models.user import User
from app.schemas.document import DocumentResponse
from app.services.exceptions import (
    DocumentNotFoundError,
    DocumentProcessingError,
)
from app.services.rag_service import RAGService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])

# Allowed file extensions
ALLOWED_EXTENSIONS = {".pdf", ".txt"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10MB


@router.post(
    "/",
    response_model=DocumentResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload document for RAG processing",
)
@limiter.limit("10/hour")  # Rate limit uploads to prevent abuse
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    title: str = Form(..., min_length=1, max_length=200),
    description: str | None = Form(None, max_length=1000),
    current_user: User = Depends(get_current_user),
    rag_service: RAGService = Depends(get_rag_service),
) -> DocumentResponse:
    """
    Upload a document and start RAG processing.

    Rate limit: 10 uploads per hour per user.

    Accepts PDF and TXT files up to 10MB. Processing is synchronous:
    - Extracts text from file
    - Chunks into 512-token segments
    - Generates embeddings via Voyage AI
    - Stores in database for semantic search

    Args:
        request: FastAPI request object (required for rate limiting)
        file: Uploaded file (multipart/form-data)
        title: Human-readable document title
        description: Optional document description
        current_user: Authenticated user from JWT token
        rag_service: RAG service for document processing

    Returns:
        DocumentResponse with status=pending (processing happens synchronously)

    Raises:
        HTTPException: 401 if authentication fails
        HTTPException: 413 if file exceeds 10MB
        HTTPException: 422 if file type not supported or processing fails
        HTTPException: 429 if rate limit exceeded
    """
    # Validate file extension
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Filename is required",
        )

    # Check extension
    import os

    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"File type {file_ext} not supported. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Read file content and check size
    file_content = await file.read()
    if len(file_content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds maximum of {MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB",
        )

    # Process document
    try:
        document = await rag_service.ingest_document(
            user_id=current_user.id,
            title=title,
            description=description,
            filename=file.filename,
            file_content=file_content,
        )

        return DocumentResponse.model_validate(document)

    except DocumentProcessingError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )


@router.get(
    "/",
    response_model=list[DocumentResponse],
    status_code=status.HTTP_200_OK,
    summary="List user's documents",
)
@limiter.limit("100/hour")  # Rate limit list operations
async def list_documents(
    request: Request,
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    rag_service: RAGService = Depends(get_rag_service),
) -> list[DocumentResponse]:
    """
    List documents for the authenticated user with pagination.

    Rate limit: 100 requests per hour per user.

    Returns documents ordered by most recently created first.

    Args:
        request: FastAPI request object (required for rate limiting)
        limit: Maximum number of documents to return (default: 20, max: 100)
        offset: Number of documents to skip for pagination (default: 0)
        current_user: Authenticated user from JWT token
        rag_service: RAG service for document operations

    Returns:
        List of documents with metadata

    Raises:
        HTTPException: 401 if authentication fails
        HTTPException: 429 if rate limit exceeded
    """
    # Clamp limit to prevent abuse
    limit = min(limit, 100)

    documents = await rag_service.list_documents(
        user_id=current_user.id,
        limit=limit,
        offset=offset,
    )

    return [DocumentResponse.model_validate(doc) for doc in documents]


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    status_code=status.HTTP_200_OK,
    summary="Get single document",
)
@limiter.limit("100/hour")  # Rate limit get operations
async def get_document(
    request: Request,
    document_id: str,
    current_user: User = Depends(get_current_user),
    rag_service: RAGService = Depends(get_rag_service),
) -> DocumentResponse:
    """
    Get a single document by ID with ownership verification.

    Rate limit: 100 requests per hour per user.

    Args:
        request: FastAPI request object (required for rate limiting)
        document_id: UUID of the document
        current_user: Authenticated user from JWT token
        rag_service: RAG service for document operations

    Returns:
        Document with metadata

    Raises:
        HTTPException: 400 if document_id format is invalid
        HTTPException: 401 if authentication fails
        HTTPException: 404 if document not found or not owned by user
        HTTPException: 429 if rate limit exceeded
    """
    from uuid import UUID

    try:
        doc_uuid = UUID(document_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid document ID format",
        )

    try:
        document = await rag_service.get_document(
            document_id=doc_uuid,
            user_id=current_user.id,
        )
        return DocumentResponse.model_validate(document)

    except DocumentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found or access denied",
        )


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete document and all its chunks",
)
@limiter.limit("100/hour")  # Rate limit delete operations
async def delete_document(
    request: Request,
    document_id: str,
    current_user: User = Depends(get_current_user),
    rag_service: RAGService = Depends(get_rag_service),
) -> None:
    """
    Delete a document and all its chunks (CASCADE handles DB side).

    Rate limit: 100 requests per hour per user.

    Args:
        request: FastAPI request object (required for rate limiting)
        document_id: UUID of the document
        current_user: Authenticated user from JWT token
        rag_service: RAG service for document operations

    Returns:
        204 No Content on success

    Raises:
        HTTPException: 400 if document_id format is invalid
        HTTPException: 401 if authentication fails
        HTTPException: 404 if document not found or not owned by user
        HTTPException: 429 if rate limit exceeded
    """
    from uuid import UUID

    try:
        doc_uuid = UUID(document_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid document ID format",
        )

    try:
        await rag_service.delete_document(
            document_id=doc_uuid,
            user_id=current_user.id,
        )

    except DocumentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found or access denied",
        )
