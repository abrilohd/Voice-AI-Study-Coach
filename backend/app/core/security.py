"""Security utilities for JWT tokens and password hashing."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from jose import JWTError, jwt

from app.core.config import settings

# Argon2 hasher with secure defaults
# Using argon2id variant (hybrid mode - best of argon2i and argon2d)
argon2_hasher = PasswordHasher(
    time_cost=3,  # Number of iterations
    memory_cost=65536,  # Memory usage in KiB (64 MiB)
    parallelism=4,  # Number of parallel threads
    hash_len=32,  # Length of the hash in bytes
    salt_len=16,  # Length of random salt in bytes
)


def utcnow() -> datetime:
    """Return current UTC time with timezone info.

    Centralized function to ensure consistent timezone-aware datetimes.

    Returns:
        Current UTC datetime with timezone info
    """
    return datetime.now(timezone.utc)


def create_access_token(subject: str) -> str:
    """Create a JWT access token.

    Args:
        subject: The subject claim (typically user ID as string)

    Returns:
        Encoded JWT access token string
    """
    expire = utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode: dict[str, Any] = {
        "exp": expire,
        "sub": subject,
        "type": "access",
    }
    encoded_jwt: str = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


def create_refresh_token() -> tuple[str, str]:
    """Create a cryptographically secure refresh token.

    Returns raw token and its SHA-256 hash as a tuple.
    We store the hash in the database, return the raw token to the client.

    Returns:
        Tuple of (raw_token, token_hash) where:
        - raw_token: 32-byte URL-safe token to return to client
        - token_hash: SHA-256 hex digest to store in database
    """
    raw_token = secrets.token_urlsafe(32)  # 32 bytes = 256 bits of entropy
    token_hash = hash_token(raw_token)
    return raw_token, token_hash


def hash_token(token: str) -> str:
    """Hash a token using SHA-256.

    Used for refresh tokens before database storage.

    Args:
        token: Raw token string to hash

    Returns:
        Hexadecimal SHA-256 hash of the token
    """
    return hashlib.sha256(token.encode()).hexdigest()


def verify_access_token(token: str) -> dict[str, Any] | None:
    """Verify and decode a JWT access token.

    Args:
        token: JWT token string to verify

    Returns:
        Decoded token payload dict or None if verification fails
    """
    try:
        payload: dict[str, Any] = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        # Verify it's an access token
        if payload.get("type") != "access":
            return None
        return payload
    except JWTError:
        return None


def hash_password(password: str) -> str:
    """Hash a password using Argon2id.

    Args:
        password: Plain text password to hash

    Returns:
        Argon2id hashed password string
    """
    return argon2_hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its Argon2 hash.

    Uses constant-time comparison to prevent timing attacks.

    Args:
        password: Plain text password to verify
        hashed: Argon2 hashed password to compare against

    Returns:
        True if password matches, False otherwise
    """
    try:
        argon2_hasher.verify(hashed, password)
        return True
    except VerifyMismatchError:
        return False
