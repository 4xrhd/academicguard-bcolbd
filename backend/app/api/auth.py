"""
auth.py — Authentication router.
FR-AUTH-01: Register  POST /auth/register
FR-AUTH-02: Login     POST /auth/login
FR-AUTH-04: Refresh   POST /auth/refresh
FR-AUTH-04: Logout    POST /auth/logout
"""
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Cookie, HTTPException, Request, Response, status
from sqlalchemy import select

from app.config import get_settings
from app.core.dependencies import CurrentUser, DBSession
from app.core.rate_limit import (
    check_login_rate_limit,
    record_failed_login,
    clear_login_attempts,
)
from app.core.security import (
    create_access_token, create_refresh_token,
    hash_password, hash_token, verify_password,
)
from app.db.models import RefreshToken, User
from app.db.schemas import LoginRequest, RegisterRequest, TokenResponse, UserResponse

router = APIRouter()
settings = get_settings()

from typing import Any
_COOKIE_OPTS: dict[str, Any] = dict(
    httponly=True, 
    secure=settings.SECURE_COOKIES, 
    samesite="lax"
)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: DBSession):
    """FR-AUTH-01 — Register a new instructor account."""
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered.")

    user = User(
        email=body.email,
        full_name=body.full_name,
        hashed_password=await hash_password(body.password),
        role="instructor",
    )
    db.add(user)
    await db.flush()
    return user


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, response: Response, request: Request, db: DBSession):
    """FR-AUTH-02 — Authenticate and issue JWT access + refresh tokens."""
    client_ip = request.client.host if request.client else ""
    await check_login_rate_limit(body.email, client_ip)

    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not await verify_password(body.password, user.hashed_password):
        await record_failed_login(body.email, client_ip)
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated.")

    await clear_login_attempts(body.email, client_ip)

    access_token = create_access_token(str(user.id), user.role)
    refresh_token = create_refresh_token(str(user.id))

    # Store hashed refresh token in DB
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    db.add(RefreshToken(
        user_id=user.id,
        token_hash=hash_token(refresh_token),
        expires_at=expires_at,
    ))

    response.set_cookie("access_token", access_token, **_COOKIE_OPTS,
                        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)
    response.set_cookie("refresh_token", refresh_token, **_COOKIE_OPTS,
                        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400)

    return TokenResponse(access_token=access_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(response: Response, db: DBSession, refresh_token: str | None = Cookie(default=None)):
    """FR-AUTH-04 — Rotate refresh token and issue new access token."""
    from app.core.security import decode_token  # noqa: F401

    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token provided.")

    payload = decode_token(refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token.")

    token_hash = hash_token(refresh_token)
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked == False,  # noqa: E712
        )
    )
    stored = result.scalar_one_or_none()
    if not stored or stored.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Refresh token expired or revoked.")

    # Revoke old token (rotation)
    stored.revoked = True

    user_id = payload["sub"]
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive.")

    new_access = create_access_token(str(user.id), user.role)
    new_refresh = create_refresh_token(str(user.id))

    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    db.add(RefreshToken(user_id=user.id, token_hash=hash_token(new_refresh), expires_at=expires_at))

    response.set_cookie("access_token", new_access, **_COOKIE_OPTS,
                        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)
    response.set_cookie("refresh_token", new_refresh, **_COOKIE_OPTS,
                        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400)

    return TokenResponse(access_token=new_access)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response, current_user: CurrentUser, db: DBSession,
                 refresh_token: str | None = Cookie(default=None)):
    """FR-AUTH-04 — Invalidate session (revoke refresh token, clear cookies)."""
    if refresh_token:
        token_hash = hash_token(refresh_token)
        result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
        stored = result.scalar_one_or_none()
        if stored:
            stored.revoked = True

    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")


@router.get("/me", response_model=UserResponse)
async def me(current_user: CurrentUser):
    """Return currently authenticated user profile."""
    return current_user
