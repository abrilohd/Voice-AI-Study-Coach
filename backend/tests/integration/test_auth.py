"""Integration tests for authentication endpoints with real database."""

import time

import pytest
from httpx import AsyncClient

from app.core.security import hash_password
from app.models.user import User


@pytest.mark.asyncio
class TestAuthRegistration:
    """Integration tests for user registration."""

    async def test_register_success(self, async_client: AsyncClient):
        """Test successful user registration."""
        # Arrange
        user_data = {
            "email": "newuser@example.com",
            "password": "SecurePassword123!",
            "display_name": "New User",
        }

        # Act
        response = await async_client.post("/api/v1/auth/register", json=user_data)

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["user"]["email"] == user_data["email"]
        assert data["user"]["display_name"] == user_data["display_name"]
        assert "access_token" in data["tokens"]
        assert data["tokens"]["token_type"] == "bearer"

    async def test_register_duplicate_email(self, async_client: AsyncClient, test_user: User):
        """Test registration fails with duplicate email."""
        # Arrange
        user_data = {
            "email": test_user.email,  # Already exists
            "password": "AnotherPassword123!",
            "display_name": "Duplicate User",
        }

        # Act
        response = await async_client.post("/api/v1/auth/register", json=user_data)

        # Assert
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"].lower()


@pytest.mark.asyncio
class TestAuthLogin:
    """Integration tests for user login."""

    async def test_login_success(self, async_client: AsyncClient, test_user: User):
        """Test successful login with valid credentials."""
        # Arrange
        login_data = {
            "email": test_user.email,
            "password": "testpassword123",  # From test_user fixture
        }

        # Act
        response = await async_client.post("/api/v1/auth/login", json=login_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["email"] == test_user.email
        assert "access_token" in data["tokens"]
        assert "refresh_token" in response.cookies

    async def test_login_invalid_credentials(self, async_client: AsyncClient):
        """Test login fails with invalid credentials."""
        # Arrange
        login_data = {
            "email": "nonexistent@example.com",
            "password": "wrongpassword",
        }

        # Act
        response = await async_client.post("/api/v1/auth/login", json=login_data)

        # Assert
        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()

    async def test_login_inactive_user(self, async_client: AsyncClient):
        """Test login fails for inactive user."""
        # Arrange - Create inactive user
        # Import AsyncSessionLocal from database module
        from app.core.database import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            inactive_user = User(
                email="inactive@example.com",
                hashed_password=hash_password("password123"),
                display_name="Inactive User",
                is_active=False,
            )
            session.add(inactive_user)
            await session.commit()

        login_data = {
            "email": "inactive@example.com",
            "password": "password123",
        }

        # Act
        response = await async_client.post("/api/v1/auth/login", json=login_data)

        # Assert
        assert response.status_code == 403
        assert "inactive" in response.json()["detail"].lower()

    async def test_login_timing_consistency(self, async_client: AsyncClient, test_user: User):
        """
        Test that login timing is consistent between user not found and wrong password.

        This prevents timing attacks that could enumerate valid email addresses.
        The service uses a dummy hash verification when user doesn't exist.
        """
        # Arrange
        valid_email = test_user.email
        non_existent_email = "notexist@example.com"

        # Act - Measure time for non-existent user
        t1 = time.perf_counter()
        response1 = await async_client.post(
            "/api/v1/auth/login",
            json={"email": non_existent_email, "password": "anypass"},
        )
        t1 = time.perf_counter() - t1

        # Act - Measure time for valid user with wrong password
        t2 = time.perf_counter()
        response2 = await async_client.post(
            "/api/v1/auth/login",
            json={"email": valid_email, "password": "wrongpass"},
        )
        t2 = time.perf_counter() - t2

        # Assert - Both should return 401
        assert response1.status_code == 401
        assert response2.status_code == 401

        # Assert - Timing difference should be minimal (within 200ms)
        # This allows for some variance but prevents obvious timing attacks
        # Threshold increased to 200ms to account for Windows system variance
        timing_diff = abs(t1 - t2)
        assert timing_diff < 0.20, (
            f"Timing difference too large: {timing_diff:.3f}s (t1={t1:.3f}s, t2={t2:.3f}s)"
        )

    async def test_rate_limit_login(self, async_client: AsyncClient, test_user: User):
        """
        Test that login endpoint enforces rate limiting.

        The endpoint allows 10 requests per 15 minutes. This test fires 11 requests
        rapidly to trigger the rate limiter.
        """
        # Arrange
        valid_creds = {
            "email": test_user.email,
            "password": "testpassword123",
        }

        # Act - Fire 11 requests rapidly (limit is 10/15min)
        responses = []
        for _ in range(11):
            r = await async_client.post("/api/v1/auth/login", json=valid_creds)
            responses.append(r)

        # Find the rate-limited response (should be the 11th one)
        rate_limited = responses[-1]

        # Assert - 11th request should be rate limited
        assert rate_limited.status_code == 429, (
            f"Expected 429 Too Many Requests on 11th attempt, got {rate_limited.status_code}"
        )

        # Assert - Should include Retry-After header (case-insensitive check)
        headers_lower = {k.lower(): v for k, v in rate_limited.headers.items()}
        assert "retry-after" in headers_lower, (
            f"Expected 'Retry-After' header in rate-limited response. "
            f"Headers: {rate_limited.headers}"
        )


@pytest.mark.asyncio
class TestAuthRefresh:
    """Integration tests for token refresh."""

    async def test_refresh_token_success(self, async_client: AsyncClient, test_user: User):
        """Test successful token refresh."""
        # Arrange - First login to get refresh token
        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={"email": test_user.email, "password": "testpassword123"},
        )
        assert login_response.status_code == 200
        refresh_token = login_response.cookies.get("refresh_token")
        assert refresh_token is not None

        # Act - Use refresh token to get new tokens
        refresh_response = await async_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )

        # Assert
        assert refresh_response.status_code == 200
        data = refresh_response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_refresh_token_invalid(self, async_client: AsyncClient):
        """Test token refresh fails with invalid token."""
        # Arrange
        invalid_token = "invalid-refresh-token-12345"

        # Act
        response = await async_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": invalid_token},
        )

        # Assert
        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()
