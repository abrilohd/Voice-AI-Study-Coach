"""Authentication schemas for request/response validation."""

import re
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

# List of the 20 most common weak passwords
COMMON_PASSWORDS = {
    "password1",
    "12345678",
    "password123",
    "123456789",
    "1234567890",
    "qwerty123",
    "abc123456",
    "password",
    "12341234",
    "87654321",
    "iloveyou",
    "password1234",
    "welcome123",
    "monkey123",
    "admin123",
    "letmein123",
    "qwertyuiop",
    "123123123",
    "000000000",
    "password12345",
}


class UserRegisterRequest(BaseModel):
    """Request schema for user registration."""

    model_config = ConfigDict(str_strip_whitespace=True)

    email: EmailStr = Field(
        description="User's email address (must be unique)",
        examples=["alice@example.com"],
    )
    password: str = Field(
        description=(
            "User's password (min 8 chars, max 128 chars, must contain uppercase and digit)"
        ),
        examples=["SecurePass123"],
        min_length=8,
        max_length=128,
    )
    display_name: str | None = Field(
        default=None,
        description="Optional display name for the user",
        examples=["Alice Johnson"],
        max_length=100,
    )

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str, info: Any) -> str:
        """
        Validate password meets security requirements.

        Rules:
        - 8-128 characters (enforced by Field constraints)
        - At least one uppercase letter
        - At least one digit
        - Must NOT contain the email address as a substring
        - Must NOT be a common weak password
        """
        # Check for at least one uppercase letter
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")

        # Check for at least one digit
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")

        # Check password is not in common passwords list
        if v.lower() in COMMON_PASSWORDS:
            raise ValueError("Password is too common, please choose a stronger password")

        # Check password does not contain email address
        # info.data contains already-validated fields
        if "email" in info.data:
            email = str(info.data["email"]).lower()
            if email in v.lower():
                raise ValueError("Password must not contain your email address")

        return v


class UserLoginRequest(BaseModel):
    """
    Request schema for user login.

    Note: No password validation here to prevent user enumeration.
    Wrong credentials return the same error as invalid format.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    email: EmailStr = Field(
        description="User's email address",
        examples=["alice@example.com"],
    )
    password: str = Field(
        description="User's password",
        examples=["SecurePass123"],
    )


class TokenResponse(BaseModel):
    """Response schema for authentication tokens."""

    model_config = ConfigDict(from_attributes=True)

    access_token: str = Field(
        description="JWT access token, expires in expires_in seconds",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."],
    )
    token_type: str = Field(
        default="bearer",
        description="Token type for Authorization header",
        examples=["bearer"],
    )
    expires_in: int = Field(
        description="Seconds until access token expiry",
        examples=[900],
    )


class UserResponse(BaseModel):
    """Response schema for user data (never exposes hashed_password)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(
        description="User's unique identifier (UUID to prevent user count leakage)",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    email: str = Field(
        description="User's email address",
        examples=["alice@example.com"],
    )
    display_name: str | None = Field(
        default=None,
        description="User's display name",
        examples=["Alice Johnson"],
    )
    is_active: bool = Field(
        description="Whether the user account is active",
        examples=[True],
    )
    created_at: datetime = Field(
        description="Timestamp when the user was created",
        examples=["2026-06-10T12:00:00Z"],
    )


class AuthResponse(BaseModel):
    """
    Response schema for successful authentication.

    Note: Never exposes refresh_token here (only in RefreshResponse).
    Refresh tokens should be returned in httpOnly cookies.
    """

    model_config = ConfigDict(from_attributes=True)

    user: UserResponse = Field(
        description="Authenticated user information",
    )
    tokens: TokenResponse = Field(
        description="Access token and metadata",
    )


class RefreshRequest(BaseModel):
    """Request schema for refreshing access tokens."""

    model_config = ConfigDict(str_strip_whitespace=True)

    refresh_token: str = Field(
        description="Valid refresh token to exchange for new access token",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."],
    )


class RefreshResponse(BaseModel):
    """Response schema for token refresh."""

    model_config = ConfigDict(from_attributes=True)

    access_token: str = Field(
        description="New JWT access token",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."],
    )
    refresh_token: str = Field(
        description="New refresh token (rotated for security)",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."],
    )
    token_type: str = Field(
        default="bearer",
        description="Token type for Authorization header",
        examples=["bearer"],
    )
    expires_in: int = Field(
        description="Seconds until access token expiry",
        examples=[900],
    )
