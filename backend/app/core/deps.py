"""
FastAPI dependency for JWT authentication.
Provides get_current_user and require_owner.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.jwt import verify_access_token
from app.models.auth import User

bearer_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract and validate the JWT bearer token, return the User."""
    token = credentials.credentials
    try:
        payload = verify_access_token(token)
        user_id: str = payload.get("sub")
        if not user_id:
            raise JWTError("Missing sub claim")
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    import uuid
    try:
        uid = uuid.UUID(user_id) if user_id else None
    except (ValueError, TypeError):
        uid = None

    result = await db.execute(select(User).where(User.id == uid))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive.")
    return user


async def require_owner(current_user: User = Depends(get_current_user)) -> User:
    """Restrict endpoint to owner role only."""
    if current_user.role != "owner":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Owner role required.")
    return current_user
