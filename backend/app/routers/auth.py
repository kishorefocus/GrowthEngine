"""
Auth router: /api/v1/auth/*
- POST /register (first user = owner; then locked)
- POST /login
- POST /refresh
- GET /google/callback (stub)
"""
import uuid
from datetime import datetime, timezone

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import APIRouter, Depends, HTTPException, Request, status
from jose import JWTError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.jwt import (
    create_access_token,
    create_refresh_token,
    hash_refresh_token,
    verify_refresh_token,
)
from app.models.auth import User
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse, UserResponse
from app.services.ratelimit import make_rate_limiter

router = APIRouter(prefix="/auth", tags=["auth"])
ph = PasswordHasher()
_auth_limiter = make_rate_limiter(max_requests=10, window_seconds=60)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(_auth_limiter),
):
    """
    Register a new user.
    - First user ever created becomes owner.
    - Subsequent registrations require an existing owner to invite (returns 403).
    """
    # Check if any user exists
    count_result = await db.execute(select(func.count()).select_from(User))
    user_count = count_result.scalar()

    if user_count > 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Registration is closed. Contact the owner to invite you.",
        )

    # Check for duplicate email
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered.")

    password_hash = ph.hash(payload.password)
    role = "owner"  # First user is always owner

    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email=payload.email,
        password_hash=password_hash,
        role=role,
    )
    db.add(user)

    # Create tokens
    access_token = create_access_token(str(user_id), role)
    refresh_token, refresh_expires = create_refresh_token(str(user_id))
    user.refresh_token_hash = hash_refresh_token(refresh_token)
    user.refresh_token_expires_at = refresh_expires

    await db.commit()
    await db.refresh(user)

    return TokenResponse(access_token=access_token, refresh_token=refresh_token, role=role)


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(_auth_limiter),
):
    """Authenticate with email + password. Returns access + refresh tokens."""
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    if not user or not user.password_hash:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")

    try:
        ph.verify(user.password_hash, payload.password)
    except VerifyMismatchError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled.")

    # Rotate refresh token on every login
    access_token = create_access_token(str(user.id), user.role)
    refresh_token, refresh_expires = create_refresh_token(str(user.id))
    user.refresh_token_hash = hash_refresh_token(refresh_token)
    user.refresh_token_expires_at = refresh_expires
    await db.commit()

    return TokenResponse(access_token=access_token, refresh_token=refresh_token, role=user.role)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    payload: RefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    """Rotate a refresh token and return a new access + refresh token pair."""
    try:
        token_data = verify_refresh_token(payload.refresh_token)
        user_id = token_data.get("sub")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token.")

    try:
        uid = uuid.UUID(user_id) if user_id else None
    except (ValueError, TypeError):
        uid = None
    result = await db.execute(select(User).where(User.id == uid))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")

    # Validate hash matches (prevents reuse of stolen old tokens)
    if user.refresh_token_hash != hash_refresh_token(payload.refresh_token):
        # Token reuse detected — invalidate all tokens
        user.refresh_token_hash = None
        await db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token reuse detected. Please log in again.")

    if user.refresh_token_expires_at:
        exp = user.refresh_token_expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp < datetime.now(timezone.utc):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired.")


    # Issue new pair
    access_token = create_access_token(str(user.id), user.role)
    new_refresh, refresh_expires = create_refresh_token(str(user.id))
    user.refresh_token_hash = hash_refresh_token(new_refresh)
    user.refresh_token_expires_at = refresh_expires
    await db.commit()

    return TokenResponse(access_token=access_token, refresh_token=new_refresh, role=user.role)


@router.get("/google/callback")
async def google_callback(code: str, state: str = "", db: AsyncSession = Depends(get_db)):
    """
    Google OAuth callback. Stub — Prompt 2/3 implements fully.
    For now, returns a not-yet-implemented message.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Google OAuth not yet implemented. Planned for Prompt 2.",
    )


from app.core.deps import get_current_user


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)):
    """
    Get current user info.
    Protected via JWT — requires valid access token.
    """
    return UserResponse(id=str(current_user.id), email=current_user.email, role=current_user.role)

