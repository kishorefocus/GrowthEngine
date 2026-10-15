"""
JWT utilities: create and verify access/refresh tokens.
- 15-minute access tokens
- Rotating refresh tokens (stored as hash in DB)
"""
import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt

from app.core.config import settings


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(user_id: str, role: str) -> str:
    """Create a 15-minute access token."""
    payload = {
        "sub": user_id,
        "role": role,
        "type": "access",
        "exp": _now() + timedelta(minutes=settings.jwt_access_token_expire_minutes),
        "iat": _now(),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(user_id: str) -> tuple[str, datetime]:
    """
    Create a refresh token. Returns (token, expires_at).
    The raw token is given to the client; only its hash is stored in DB.
    """
    expires_at = _now() + timedelta(days=settings.jwt_refresh_token_expire_days)
    payload = {
        "sub": user_id,
        "type": "refresh",
        "exp": expires_at,
        "iat": _now(),
        "jti": str(uuid.uuid4()),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, expires_at


def hash_refresh_token(token: str) -> str:
    """Hash a refresh token for storage. Never store raw tokens."""
    return hashlib.sha256(token.encode()).hexdigest()


def verify_access_token(token: str) -> dict:
    """Verify and decode an access token. Raises JWTError on failure."""
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    if payload.get("type") != "access":
        raise JWTError("Not an access token")
    return payload


def verify_refresh_token(token: str) -> dict:
    """Verify and decode a refresh token. Raises JWTError on failure."""
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    if payload.get("type") != "refresh":
        raise JWTError("Not a refresh token")
    return payload
