"""Security utilities for JWT tokens and password hashing."""

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """
    Create a JWT access token.

    Args:
        data: Dictionary of claims to encode in the token.
        expires_delta: Optional custom expiration time. Defaults to settings value.

    Returns:
        Encoded JWT token string.
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.access_token_expire_minutes
        )

    to_encode.update({"exp": expire})
    encoded_jwt: str = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


def create_refresh_token(subject: str) -> str:
    """
    Create a JWT refresh token.

    Args:
        subject: The subject (typically user ID) for the token.

    Returns:
        Encoded JWT refresh token string.
    """
    expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    to_encode: dict[str, Any] = {"exp": expire, "sub": subject}
    encoded_jwt: str = jwt.encode(
        to_encode, settings.secret_key, algorithm=settings.algorithm
    )
    return encoded_jwt


def verify_token(token: str) -> dict[str, Any] | None:
    """
    Verify and decode a JWT token.

    Args:
        token: JWT token string to verify.

    Returns:
        Decoded token payload as a dictionary, or None if verification fails.
    """
    try:
        payload: dict[str, Any] = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        return payload
    except JWTError:
        return None


def get_password_hash(password: str) -> str:
    """
    Hash a plain text password.

    Args:
        password: Plain text password to hash.

    Returns:
        Bcrypt hashed password string.
    """
    hashed: str = pwd_context.hash(password)
    return hashed


def verify_password(plain: str, hashed: str) -> bool:
    """
    Verify a plain text password against a hashed password.

    Args:
        plain: Plain text password to verify.
        hashed: Hashed password to compare against.

    Returns:
        True if password matches, False otherwise.
    """
    result: bool = pwd_context.verify(plain, hashed)
    return result
