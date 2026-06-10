"""Pytest configuration and fixtures for testing."""

import asyncio
from collections.abc import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.user import User


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """
    Create an event loop for the entire test session.

    Yields:
        Event loop for async tests.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def engine():
    """
    Create an async in-memory SQLite engine for testing.

    Creates all tables from Base.metadata at the start of each test.

    Yields:
        AsyncEngine: In-memory SQLite engine with all tables created.
    """
    # Create in-memory SQLite engine with aiosqlite driver
    test_engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        pool_pre_ping=True,
    )

    # Create all tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield test_engine

    # Clean up
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await test_engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Create a database session for each test function.

    Rolls back all changes after each test to ensure test isolation.

    Args:
        engine: The async SQLite engine fixture.

    Yields:
        AsyncSession: Database session for the test.
    """
    # Create session factory
    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async with async_session_maker() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def async_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Create an httpx AsyncClient for testing API endpoints.

    Overrides the get_db dependency to use the test database session.

    Args:
        db_session: The test database session fixture.

    Yields:
        AsyncClient: HTTP client configured for testing.
    """

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        """Override get_db dependency to use test database."""
        yield db_session

    # Override the dependency
    app.dependency_overrides[get_db] = override_get_db

    # Create async client
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    # Clean up dependency override
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def test_user(db_session: AsyncSession) -> User:
    """
    Create a test user in the database.

    Creates a user with:
    - email: test@example.com
    - password: testpassword123 (hashed)
    - display_name: Test User
    - is_active: True

    Args:
        db_session: The test database session fixture.

    Returns:
        User: The created test user ORM object.
    """
    # Create test user
    user = User(
        email="test@example.com",
        hashed_password=hash_password("testpassword123"),
        display_name="Test User",
        is_active=True,
    )

    # Add to database
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    return user


@pytest_asyncio.fixture(scope="function")
async def auth_headers(test_user: User) -> dict[str, str]:
    """
    Create authorization headers with a valid access token for the test user.

    Args:
        test_user: The test user fixture.

    Returns:
        dict: Dictionary containing Authorization header with Bearer token.
    """
    # Create access token with user's email as subject
    access_token = create_access_token(data={"sub": test_user.email})

    return {"Authorization": f"Bearer {access_token}"}
