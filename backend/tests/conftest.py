"""Pytest configuration and fixtures for testing."""

import asyncio
import tempfile
from collections.abc import AsyncGenerator, Generator
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Create a persistent test database file
_temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_test_db_path = Path(_temp_db.name)
_temp_db.close()

# Create test engine
_test_engine = create_async_engine(
    f"sqlite+aiosqlite:///{_test_db_path}",
    echo=False,
    pool_pre_ping=True,
)

# Create test session factory
_test_session_maker = async_sessionmaker(
    _test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Patch the app's database module BEFORE importing app.main
import app.core.database as db_module  # noqa: E402

db_module.engine = _test_engine
db_module.AsyncSessionLocal = _test_session_maker

# NOW import the app and other dependencies
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.core.database import Base  # noqa: E402
from app.core.security import create_access_token, hash_password  # noqa: E402
from app.main import app  # noqa: E402
from app.models.user import User  # noqa: E402


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


@pytest_asyncio.fixture(scope="function", autouse=True)
async def setup_database():
    """
    Create and clean up database tables for each test.

    This fixture automatically runs for every test function, creating all tables
    at the start and dropping them at the end to ensure test isolation.

    Also clears rate limiter state to prevent rate limits from affecting
    subsequent tests.

    Yields:
        None
    """
    # Clear rate limiter storage between tests
    from app.core.dependencies import limiter

    limiter.reset()

    # Create all tables
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    # Drop all tables
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """
    Create an httpx AsyncClient for testing API endpoints.

    The app will use the test database that was configured via DATABASE_URL
    environment variable at module import time.

    Yields:
        AsyncClient: HTTP client configured for testing.
    """
    # Create async client - app already uses test database
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


@pytest_asyncio.fixture(scope="function")
async def test_user() -> User:
    """
    Create a test user in the database.

    Creates a user with:
    - email: test@example.com
    - password: testpassword123 (hashed)
    - display_name: Test User
    - is_active: True

    Returns:
        User: The created test user ORM object.
    """
    # Import AsyncSessionLocal from database module
    from app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        # Create test user
        user = User(
            email="test@example.com",
            hashed_password=hash_password("testpassword123"),
            display_name="Test User",
            is_active=True,
        )

        # Add to database
        session.add(user)
        await session.commit()
        await session.refresh(user)

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
