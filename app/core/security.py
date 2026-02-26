"""Security utilities for password hashing and JWT token management."""

import secrets
import hashlib
import bcrypt
from datetime import datetime, timedelta, timezone
from uuid import UUID

from jose import jwt, JWTError

from app.core.config import settings


def generate_salt() -> str:
    """Generate a random salt for password hashing."""
    return secrets.token_hex(32)


def _prepare_password(password: str, salt: str) -> bytes:
    """SHA-256 hash the salted password to produce a fixed 32-byte input for bcrypt.

    bcrypt truncates inputs at 72 bytes. Since the stored salt alone is 64 hex
    chars, concatenating it with the password would leave almost no room for the
    actual password. Pre-hashing collapses the combined string to exactly 32 bytes
    regardless of password length, while still binding the salt to the hash.
    """
    return hashlib.sha256(f"{password}{salt}".encode("utf-8")).digest()


def hash_password(password: str, salt: str) -> str:
    """Hash a password with the given salt, returning a UTF-8 bcrypt string."""
    return bcrypt.hashpw(_prepare_password(password, salt), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, salt: str, password_hash: str) -> bool:
    """Verify a password against a stored bcrypt hash."""
    return bcrypt.checkpw(_prepare_password(password, salt), password_hash.encode("utf-8"))


def create_jwt_token(user_id: UUID, expires_delta: timedelta | None = None) -> str:
    """
    Create a JWT token for the given user.
    
    Args:
        user_id: The user's UUID
        expires_delta: Optional custom expiration time
        
    Returns:
        The encoded JWT token
    """
    if expires_delta is None:
        expires_delta = timedelta(hours=settings.jwt_expiry_hours)
    
    expire = datetime.now(timezone.utc) + expires_delta
    
    payload = {
        "sub": str(user_id),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_jwt_token(token: str) -> dict | None:
    """
    Decode and validate a JWT token.
    
    Args:
        token: The JWT token to decode
        
    Returns:
        The decoded payload if valid, None otherwise
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError:
        return None


def get_user_id_from_token(token: str) -> UUID | None:
    """
    Extract the user ID from a JWT token.
    
    Args:
        token: The JWT token
        
    Returns:
        The user's UUID if valid, None otherwise
    """
    payload = decode_jwt_token(token)
    if payload is None:
        return None
    
    user_id_str = payload.get("sub")
    if user_id_str is None:
        return None
    
    try:
        return UUID(user_id_str)
    except ValueError:
        return None


def generate_session_token() -> str:
    """Generate a secure random session token."""
    return secrets.token_urlsafe(32)
