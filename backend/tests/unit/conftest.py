"""Unit test fixtures with AsyncMock for fast testing without database."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.models.user import User
from app.repositories.user_repository import UserRepository


def fake_user(
    user_id: str | None = None,
    email: str = "test@example.com",
    hashed_password: str = "$argon2id$v=19$m=65536,t=3,p=4$fake",
    display_name: str = "Test User",
    is_active: bool = True,
) -> User:
    """
    Create a fake User ORM object for testing.

    Args:
        user_id: User UUID (generates new one if not provided)
        email: User email address
        hashed_password: Pre-hashed password
        display_name: User display name
        is_active: User active status

    Returns:
        User: Fake user ORM object with all fields populated
    """
    user = User(
        id=uuid4() if user_id is None else user_id,
        email=email,
        hashed_password=hashed_password,
        display_name=display_name,
        is_active=is_active,
    )
    return user


@pytest.fixture
def mock_repo() -> AsyncMock:
    """
    Create a mocked UserRepository with common default behaviors.

    Default behaviors:
    - email_exists() returns False
    - create() returns a fake user
    - get_by_email() returns None
    - All other methods return None by default

    Returns:
        AsyncMock: Mocked repository with UserRepository spec
    """
    repo = AsyncMock(spec=UserRepository)
    repo.email_exists.return_value = False
    repo.create.return_value = fake_user()
    repo.get_by_email.return_value = None
    return repo


@pytest.fixture
def mock_db() -> AsyncMock:
    """
    Create a mocked AsyncSession for database operations.

    Provides commit, rollback, and refresh methods as no-ops.

    Returns:
        AsyncMock: Mocked database session
    """
    db = AsyncMock()
    db.commit.return_value = None
    db.rollback.return_value = None
    db.refresh.return_value = None
    return db
