"""Dependency injection for FastAPI routes."""

from collections.abc import AsyncGenerator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.security import verify_access_token
from app.models.user import User
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.services.chat_service import ChatService
from app.services.rag_service import RAGService

# Rate limiter instance using client IP address as key
limiter = Limiter(key_func=get_remote_address)

# HTTP Bearer token scheme for JWT authentication
security = HTTPBearer()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for database session injection.

    Yields:
        AsyncSession: Database session for the request lifecycle

    Example:
        ```python
        @router.get("/users")
        async def list_users(db: AsyncSession = Depends(get_db)):
            # Use db session here
        ```
    """
    async with AsyncSessionLocal() as session:
        yield session


async def get_user_repository(db: AsyncSession = Depends(get_db)) -> UserRepository:
    """
    Dependency for user repository injection.

    Args:
        db: Database session from get_db dependency

    Returns:
        UserRepository: Repository instance for user operations

    Example:
        ```python
        @router.get("/users/{user_id}")
        async def get_user(
            user_id: UUID,
            user_repo: UserRepository = Depends(get_user_repository)
        ):
            return await user_repo.get_by_id(user_id)
        ```
    """
    return UserRepository(db)


async def get_auth_service(
    user_repo: UserRepository = Depends(get_user_repository),
    db: AsyncSession = Depends(get_db),
) -> AuthService:
    """
    Dependency for auth service injection.

    Args:
        user_repo: User repository from get_user_repository dependency
        db: Database session from get_db dependency

    Returns:
        AuthService: Service instance for authentication operations

    Example:
        ```python
        @router.post("/register")
        async def register(
            request: UserRegisterRequest,
            auth_service: AuthService = Depends(get_auth_service)
        ):
            return await auth_service.register(...)
        ```
    """
    return AuthService(user_repo, db)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    user_repo: UserRepository = Depends(get_user_repository),
) -> User:
    """
    Dependency for extracting and validating current authenticated user from JWT.

    Args:
        credentials: HTTP Bearer credentials from Authorization header
        user_repo: User repository for database queries

    Returns:
        User: Authenticated user instance

    Raises:
        HTTPException: 401 if token is invalid, expired, or user not found
        HTTPException: 403 if user account is inactive

    Example:
        ```python
        @router.get("/profile")
        async def get_profile(
            current_user: User = Depends(get_current_user)
        ):
            return {"email": current_user.email}
        ```
    """
    # Verify and decode JWT access token
    payload = verify_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extract user email from token subject
    email: str | None = payload.get("sub")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Fetch user from database
    user = await user_repo.get_by_email(email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user account is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account",
        )

    return user


async def get_conversation_repository(
    db: AsyncSession = Depends(get_db),
) -> ConversationRepository:
    """
    Dependency for conversation repository injection.

    Args:
        db: Database session from get_db dependency

    Returns:
        ConversationRepository: Repository instance for conversation operations

    Example:
        ```python
        @router.get("/conversations/{conversation_id}")
        async def get_conversation(
            conversation_id: UUID,
            conv_repo: ConversationRepository = Depends(get_conversation_repository)
        ):
            return await conv_repo.get_by_id(conversation_id)
        ```
    """
    return ConversationRepository(db)


async def get_chat_service(
    conv_repo: ConversationRepository = Depends(get_conversation_repository),
    db: AsyncSession = Depends(get_db),
) -> ChatService:
    """
    Dependency for chat service injection.

    Args:
        conv_repo: Conversation repository from get_conversation_repository dependency
        db: Database session from get_db dependency

    Returns:
        ChatService: Service instance for chat operations

    Example:
        ```python
        @router.post("/chat/stream")
        async def stream_chat(
            request: ChatRequest,
            chat_service: ChatService = Depends(get_chat_service)
        ):
            return await chat_service.stream_response(...)
        ```
    """
    return ChatService(conv_repo, db)


async def get_document_repository(
    db: AsyncSession = Depends(get_db),
) -> DocumentRepository:
    """
    Dependency for document repository injection.

    Args:
        db: Database session from get_db dependency

    Returns:
        DocumentRepository: Repository instance for document operations

    Example:
        ```python
        @router.get("/documents/{document_id}")
        async def get_document(
            document_id: UUID,
            doc_repo: DocumentRepository = Depends(get_document_repository)
        ):
            return await doc_repo.get_by_id(document_id)
        ```
    """
    return DocumentRepository(db)


async def get_rag_service(
    doc_repo: DocumentRepository = Depends(get_document_repository),
    db: AsyncSession = Depends(get_db),
) -> RAGService:
    """
    Dependency for RAG service injection.

    Args:
        doc_repo: Document repository from get_document_repository dependency
        db: Database session from get_db dependency

    Returns:
        RAGService: Service instance for RAG operations

    Example:
        ```python
        @router.post("/documents/upload")
        async def upload_document(
            file: UploadFile,
            rag_service: RAGService = Depends(get_rag_service)
        ):
            return await rag_service.ingest_document(...)
        ```
    """
    return RAGService(doc_repo, db)
