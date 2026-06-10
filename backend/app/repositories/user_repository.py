"""User repository for database operations."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository:
    """Repository for User database operations.

    NOTE: This repository NEVER calls commit() or rollback().
    Session lifecycle management belongs to the caller (service layer).
    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            db: Async SQLAlchemy session
        """
        self.db = db

    async def get_by_id(self, user_id: UUID) -> User | None:
        """Get user by ID.

        Args:
            user_id: User ID

        Returns:
            User object or None if not found
        """
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        """Get user by email (case-insensitive).

        Args:
            email: User email address

        Returns:
            User object or None if not found
        """
        result = await self.db.execute(
            select(User).where(func.lower(User.email) == func.lower(email))
        )
        return result.scalar_one_or_none()

    async def email_exists(self, email: str) -> bool:
        """Check if email exists (case-insensitive, lightweight query).

        Does not load full ORM object - uses SELECT 1 for efficiency.

        Args:
            email: Email address to check

        Returns:
            True if email exists, False otherwise
        """
        result = await self.db.execute(
            select(1).where(func.lower(User.email) == func.lower(email)).limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def create(
        self,
        email: str,
        hashed_password: str,
        display_name: str | None = None,
    ) -> User:
        """Create a new user.

        Uses flush() not commit() - caller is responsible for commit.

        Args:
            email: User email address
            hashed_password: Already hashed password
            display_name: Optional display name

        Returns:
            Created User object
        """
        user = User(
            email=email,
            hashed_password=hashed_password,
            display_name=display_name,
        )
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def update_last_active(self, user_id: UUID) -> None:
        """Update user's last active timestamp.

        Sets updated_at to current time. NO commit - caller commits.

        Args:
            user_id: User ID
        """
        await self.db.execute(update(User).where(User.id == user_id).values(updated_at=func.now()))

    async def deactivate(self, user_id: UUID) -> None:
        """Deactivate a user account.

        Sets is_active to False. NO commit - caller commits.

        Args:
            user_id: User ID
        """
        await self.db.execute(update(User).where(User.id == user_id).values(is_active=False))

    async def set_refresh_token(
        self,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> None:
        """Store hashed refresh token for user.

        NO commit - caller commits.

        Args:
            user_id: User ID
            token_hash: Hashed refresh token
            expires_at: Token expiration datetime
        """
        await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                refresh_token_hash=token_hash,
                refresh_token_expires_at=expires_at,
            )
        )

    async def get_by_refresh_token_hash(self, token_hash: str) -> User | None:
        """Get user by refresh token hash if token is still valid.

        Checks that expires_at > now().

        Args:
            token_hash: Hashed refresh token

        Returns:
            User object or None if token invalid/expired
        """
        result = await self.db.execute(
            select(User).where(
                User.refresh_token_hash == token_hash,
                User.refresh_token_expires_at > func.now(),
            )
        )
        return result.scalar_one_or_none()

    async def clear_refresh_token(self, user_id: UUID) -> None:
        """Clear refresh token for user (logout).

        Sets token_hash and expires_at to None. NO commit - caller commits.

        Args:
            user_id: User ID
        """
        await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                refresh_token_hash=None,
                refresh_token_expires_at=None,
            )
        )
