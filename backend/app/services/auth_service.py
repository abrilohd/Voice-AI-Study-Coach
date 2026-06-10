"""Authentication service for user registration, login, and token management."""

from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    argon2_hasher,
    create_access_token,
    create_refresh_token,
    hash_token,
    utcnow,
)
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.exceptions import (
    InvalidCredentialsError,
    InvalidTokenError,
    UserAlreadyExistsError,
    UserInactiveError,
)


@dataclass
class AuthResult:
    """Result of successful authentication (register or login).

    Attributes:
        user: The authenticated user ORM model
        access_token: JWT access token for API requests
        refresh_token: Raw refresh token for token rotation
    """

    user: User
    access_token: str
    refresh_token: str


@dataclass
class TokenPair:
    """Pair of access and refresh tokens from token refresh operation.

    Attributes:
        access_token: New JWT access token
        refresh_token: New refresh token (rotated for security)
    """

    access_token: str
    refresh_token: str


class AuthService:
    """Service for user authentication and token management.

    This service handles:
    - User registration with password hashing
    - User login with constant-time credential verification
    - Refresh token rotation
    - Logout (token revocation)

    All methods commit once at the end to maintain transaction atomicity.
    """

    def __init__(self, user_repo: UserRepository, db: AsyncSession) -> None:
        """Initialize auth service with repository and database session.

        Args:
            user_repo: Repository for user database operations
            db: Async database session for transaction control
        """
        self.user_repo = user_repo
        self.db = db

    async def register(
        self,
        email: str,
        password: str,
        display_name: str | None = None,
    ) -> AuthResult:
        """Register a new user account.

        Creates user, hashes password with Argon2, generates tokens.
        Commits transaction once at the end.

        Args:
            email: User's email address (must be unique)
            password: Plain text password (will be hashed)
            display_name: Optional display name

        Returns:
            AuthResult with user, access token, and refresh token

        Raises:
            UserAlreadyExistsError: If email already exists
        """
        # Check for existing email
        if await self.user_repo.email_exists(email):
            raise UserAlreadyExistsError(email)

        # Hash password with Argon2id
        hashed_password = argon2_hasher.hash(password)

        # Create user (repository calls flush, not commit)
        user = await self.user_repo.create(email, hashed_password, display_name)

        # Generate access token with user ID
        access_token = create_access_token(str(user.id))

        # Generate refresh token and store its hash
        raw_refresh, token_hash = create_refresh_token()
        expires_at = utcnow() + timedelta(days=settings.refresh_token_expire_days)
        await self.user_repo.set_refresh_token(user.id, token_hash, expires_at)

        # ONE commit for the whole operation
        await self.db.commit()
        await self.db.refresh(user)

        return AuthResult(
            user=user,
            access_token=access_token,
            refresh_token=raw_refresh,
        )

    async def login(self, email: str, password: str) -> AuthResult:
        """Authenticate user with email and password.

        Uses constant-time comparison with dummy hash to prevent timing attacks.
        Always verifies a hash (real or dummy) to prevent user enumeration.

        Args:
            email: User's email address
            password: Plain text password to verify

        Returns:
            AuthResult with user, access token, and refresh token

        Raises:
            InvalidCredentialsError: If credentials are invalid
            UserInactiveError: If user account is inactive
        """
        # Fetch user by email
        user = await self.user_repo.get_by_email(email)

        # Use dummy hash if user doesn't exist (prevents timing attack)
        dummy_hash = settings.dummy_hash
        hash_to_check = user.hashed_password if user else dummy_hash

        # Always verify a hash - takes same time whether user exists or not
        try:
            argon2_hasher.verify(hash_to_check, password)
            valid = True
        except Exception:
            valid = False

        # Check credentials after constant-time verification
        if not user or not valid:
            raise InvalidCredentialsError()

        # Check if user is active
        if not user.is_active:
            raise UserInactiveError()

        # Generate new tokens
        access_token = create_access_token(str(user.id))
        raw_refresh, token_hash = create_refresh_token()
        expires_at = utcnow() + timedelta(days=settings.refresh_token_expire_days)

        # Rotate refresh token
        await self.user_repo.set_refresh_token(user.id, token_hash, expires_at)

        # Update last active timestamp
        await self.user_repo.update_last_active(user.id)

        # ONE commit for the whole operation
        await self.db.commit()
        await self.db.refresh(user)

        return AuthResult(
            user=user,
            access_token=access_token,
            refresh_token=raw_refresh,
        )

    async def refresh_tokens(self, refresh_token: str) -> TokenPair:
        """Exchange a refresh token for new access and refresh tokens.

        Implements refresh token rotation - old token is invalidated,
        new token is generated. This limits the damage from token theft.

        Args:
            refresh_token: Raw refresh token from client

        Returns:
            TokenPair with new access and refresh tokens

        Raises:
            InvalidTokenError: If refresh token is invalid or expired
        """
        # Hash the token to compare with database
        token_hash = hash_token(refresh_token)

        # Find user by token hash (also checks expiration)
        user = await self.user_repo.get_by_refresh_token_hash(token_hash)
        if not user:
            raise InvalidTokenError()

        # Check if user is active
        if not user.is_active:
            raise UserInactiveError()

        # Generate new token pair
        access_token = create_access_token(str(user.id))
        raw_refresh, new_token_hash = create_refresh_token()
        expires_at = utcnow() + timedelta(days=settings.refresh_token_expire_days)

        # Rotate the refresh token
        await self.user_repo.set_refresh_token(user.id, new_token_hash, expires_at)

        # Update last active timestamp
        await self.user_repo.update_last_active(user.id)

        # ONE commit for the whole operation
        await self.db.commit()

        return TokenPair(
            access_token=access_token,
            refresh_token=raw_refresh,
        )

    async def logout(self, user_id: UUID) -> None:
        """Logout user by invalidating their refresh token.

        Clears refresh token hash and expiration from database.

        Args:
            user_id: ID of user to logout
        """
        await self.user_repo.clear_refresh_token(user_id)

        # ONE commit for the whole operation
        await self.db.commit()
