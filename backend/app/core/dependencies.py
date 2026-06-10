"""Dependency injection for FastAPI routes."""

from collections.abc import AsyncGenerator

from fastapi import Depends
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService

# Rate limiter instance using client IP address as key
limiter = Limiter(key_func=get_remote_address)


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
